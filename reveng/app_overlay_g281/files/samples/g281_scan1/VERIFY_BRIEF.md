# Independent re-read of quotes (read-only, $0)

You get a checklist JSON: items[] each with id and checks[] {evidenceId,url,kind,quote}. You have NOT seen anyone's conclusions; only judge whether each quote is on the page. For every check, open the URL with WebFetch (do NOT use WebSearch; if a page cannot be fetched, try the same URL once more, then mark it unreachable) and compare:
- confirmed: the quote (or a trivially different rendering of it) is on the page and means what the quote says, including any figure.
- partially_supported: the page supports it but a number, qualifier or wording differs materially (explain in `note`, give the page's own wording).
- contradicted: the page says something that conflicts with the quote.
- not_found: page opened but the statement is nowhere on it.
- unreachable: the page could not be opened (refused, error, paywall). Do not guess.
Rules: public pages only, as a normal reader; no logins, no scraping software, no contacting anyone. Never invent a snippet: `pageSnippet` must be copied from the page you opened (<= 300 chars), or empty for unreachable.
Output: write JSON `{ "results": [ {candidateId,evidenceId,url,status,note,pageSnippet}, ... ] }` (one entry per check, same order) to the file path given in the task, then validate it is valid JSON with `node -e "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" <file>`.
Final reply: max 4 lines: counts per status and any contradicted/not_found items by id.
