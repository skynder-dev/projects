import copy
import datetime as dt
import os
import tempfile
import unittest
import wave
from pathlib import Path

from socialreel import grants
from socialreel.claims import build_claims, extract_tokens, validate_script
from socialreel.common import ROOT, money, parse_date, read_json
from socialreel.voice import speech_text
from socialreel.writer import template_script

FIX = ROOT / "fixtures" / "grants_gov_normalized_20261003.json"
TODAY = dt.date(2026, 10, 10)
SNAP = {"file": "fixture", "sha256": "0" * 64}


def recs():
    return {r["normalized_facts"]["opportunity_id"]: grants.from_fixture(r) for r in read_json(FIX)}


class Basics(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(parse_date("11/17/2026"), dt.date(2026, 11, 17))
        self.assertEqual(parse_date("2026-11-17"), dt.date(2026, 11, 17))
        self.assertEqual(parse_date("Nov 17, 2026 12:00:00 AM EST"), dt.date(2026, 11, 17))
        self.assertEqual(parse_date("11172026"), dt.date(2026, 11, 17))
        self.assertIsNone(parse_date("soon"))

    def test_money_exact(self):
        self.assertEqual(money(650000), "$650,000")
        self.assertEqual(money(24750000), "$24.75 million")
        self.assertEqual(money(250143), "$250,143")
        self.assertEqual(money(1234567), "$1,234,567")   # not exact in millions -> full digits

    def test_tokens(self):
        t = extract_tokens("Up to $650,000 each, $24.75 million total, closes Nov 17, 2026; 12 awards.")
        self.assertIn(650000.0, t["money"])
        self.assertIn(24750000.0, t["money"])
        self.assertIn((11, 17, 2026), t["dates"])
        self.assertEqual(t["numbers"], ["12"])

    def test_speech(self):
        s = speech_text("Up to $650,000. Closes November 17, 2026 on Grants.gov.")
        self.assertIn("650,000 dollars", s)
        self.assertIn("November 17th", s)
        self.assertIn("Grants dot gov", s)


class ClaimsAndScripts(unittest.TestCase):
    def test_claims_for_usda(self):
        c = {x["key"]: x for x in build_claims(recs()["364020"], SNAP, TODAY)}
        self.assertEqual(c["award_range"]["values"], {"award_floor": 600000, "award_ceiling": 650000})
        self.assertEqual(c["total_funding"]["values"]["estimated_total_program_funding"], 24750000)
        self.assertEqual(c["deadline"]["values"]["date"], "2026-11-17")
        self.assertIn("eligibility_restricted", c)
        for x in c.values():
            self.assertTrue(x["source"]["url"].startswith("https://www.grants.gov/"))

    def test_expired_deadline_is_not_claimed(self):
        c = {x["key"] for x in build_claims(recs()["363996"], SNAP, dt.date(2026, 11, 5))}
        self.assertNotIn("deadline", c)

    def test_template_scripts_validate(self):
        for oid in ("364020", "363996"):
            rec = recs()[oid]
            claims = build_claims(rec, SNAP, TODAY)
            s = template_script(rec, claims)
            self.assertEqual(validate_script(s, claims), [], oid)

    def _base(self):
        rec = recs()["364020"]
        claims = build_claims(rec, SNAP, TODAY)
        return template_script(rec, claims), claims

    def test_rejects_invented_amount(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        s["segments"][0]["voiceover"] = "Up to $700,000 per award."
        self.assertTrue(any("amount" in e for e in validate_script(s, claims)))

    def test_rejects_amount_from_uncited_claim(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        s["segments"][0]["voiceover"] += " Total funding is $24.75 million."   # total_funding not cited here
        self.assertTrue(any("amount" in e for e in validate_script(s, claims)))

    def test_rejects_invented_date(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        dl = next(x for x in s["segments"] if x["role"] == "deadline")
        dl["voiceover"] = "Applications close November 30, 2026."
        self.assertTrue(any("date" in e for e in validate_script(s, claims)))

    def test_rejects_hype_and_vague(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        s["segments"][1]["voiceover"] += " This is free money and thousands of founders get it."
        errs = validate_script(s, claims)
        self.assertTrue(any("banned" in e for e in errs))
        self.assertTrue(any("vague" in e for e in errs))

    def test_rejects_unknown_claim(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        s["segments"][1]["claim_keys"] = ["made_up"]
        self.assertTrue(any("unknown claim" in e for e in validate_script(s, claims)))

    def test_requires_official_source_close(self):
        s, claims = self._base()
        s = copy.deepcopy(s)
        s["segments"][-1]["voiceover"] = "Thanks for watching."
        s["segments"][-1]["on_screen"] = {}
        self.assertTrue(any("last segment" in e for e in validate_script(s, claims)))


class Normalize(unittest.TestCase):
    def test_normalize_api_shape(self):
        # Synthetic record shaped like the documented search2 hit + fetchOpportunity data.
        hit = {"id": "999001", "number": "ABC-123", "title": "Test Program", "agencyCode": "DOT-FTA",
               "openDate": "10/01/2026", "closeDate": "12/01/2026", "oppStatus": "posted", "docType": "synopsis"}
        det = {"id": 999001, "opportunityNumber": "ABC-123", "opportunityTitle": "Test Program",
               "owningAgencyCode": "DOT-FTA",
               "synopsis": {"agencyName": "Federal Transit Administration", "synopsisDesc": "<p>Funds buses.</p>",
                            "awardCeiling": "1000000", "awardFloor": "0", "estimatedFunding": "5000000",
                            "expectedNumberOfAwards": "5", "costSharing": False,
                            "applicantTypes": [{"id": "05", "description": "Small businesses"}],
                            "fundingInstruments": [{"id": "G", "description": "Grant"}]}}
        r = grants.normalize(hit, det)
        self.assertEqual(r["award_ceiling"], 1000000)
        self.assertIsNone(r["award_floor"])                 # "0" means not listed
        self.assertEqual(r["applicant_types"], ["Small businesses"])
        self.assertEqual(r["top_agency"], "U.S. Department of Transportation")
        self.assertEqual(r["fields"]["award_ceiling"], "synopsis.awardCeiling")
        self.assertEqual(r["description"], "Funds buses.")


class RenderSmoke(unittest.TestCase):
    def test_render_two_segments(self):
        from socialreel.render import build_audio, render_video
        from socialreel.verify import probe
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            wavs = []
            for i in range(2):
                p = d / f"s{i}.wav"
                with wave.open(str(p), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
                    w.writeframes(b"\x00\x00" * 22050)
                wavs.append(p)
            durs = build_audio(wavs, d / "n.wav")
            segs = [{"visual": "hook", "on_screen": {"kicker": "UP TO", "big": "$650,000", "headline": "per award"}},
                    {"visual": "source", "on_screen": {"kicker": "CHECK", "headline": "OST-OSDBU-2027-SBTTAC-REGION1-FY2027-1"}}]
            render_video(segs, durs, d / "n.wav", d / "o.mp4", "Source: test\nline 2", d / "stills")
            v = next(s for s in probe(d / "o.mp4")["streams"] if s["codec_type"] == "video")
            self.assertEqual((v["width"], v["height"]), (1080, 1920))


if __name__ == "__main__":
    unittest.main()
