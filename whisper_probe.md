# Whisper models on the NASA interview (9 min, CPU int8)

- Systran/faster-whisper-small: 118.0 s to hear 556.0 s (3.5 s to load), 1383 words
- Systran/faster-distil-whisper-large-v3: 170.4 s to hear 556.0 s (7.1 s to load), 1388 words
- deepdml/faster-whisper-large-v3-turbo-ct2: 214.6 s to hear 556.0 s (7.7 s to load), 1383 words
- Systran/faster-whisper-large-v3: 946.7 s to hear 556.0 s (13.1 s to load), 1380 words

## Word error rate against Systran/faster-whisper-large-v3 (no human transcript: the biggest model as the reference)

- Systran/faster-whisper-small: 2.5 %
- Systran/faster-distil-whisper-large-v3: 2.5 %
- deepdml/faster-whisper-large-v3-turbo-ct2: 1.7 %

### Where Systran/faster-whisper-small hears otherwise (Systran/faster-whisper-large-v3 -> Systran/faster-whisper-small)

- 25 s: ...check. Station, this is **Gio Benitez** -> **Geo Bonitas**
- 35 s: ...ready for the event. **-** -> **Oh,**
- 36 s: ...for the event. Commander **Mann,** -> **-Man,**
- 56 s: ...exceeded. It's very busy **on board** -> **onboard**
- 85 s: ...training, it is really **an** -> **-**
- 88 s: ...sense of emotions. There's, **you know,** -> **-**
- 96 s: ...have ahead of us **on board** -> **onboard**
- 165 s: ...wasn't a little bit **until** -> **to**
- 254 s: ...human science, specifically a **biobrow** -> **bi -bro**
- 349 s: ...we have a couple **spacewalks** -> **of space walks**
- 384 s: ...concept that Earth is **-** -> **is**
- 406 s: ...it makes it very, **very important. It's** -> **-**
- 440 s: ...all of your food. **I'm very excited** -> **-**
- 474 s: ...Russian colleagues there now? **-** -> **On board the Space Station, I think**
- 474 s: ...now? We have a **-** -> **very**
- 497 s: ...that is our mission **-** -> **of**
- 524 s: ...Station. Please stand by **while** -> **where**

### Where Systran/faster-distil-whisper-large-v3 hears otherwise (Systran/faster-whisper-large-v3 -> Systran/faster-distil-whisper-large-v3)

- 35 s: ...ready for the event. **-** -> **Oh,**
- 36 s: ...for the event. Commander **Mann,** -> **Man,**
- 75 s: ...Space Station? Well, I **didn't** -> **did**
- 81 s: ...was an amazing experience. **-** -> **experience.**
- 85 s: ...training, it is really **an** -> **-**
- 86 s: ...is really an overwhelming **-** -> **a**
- 118 s: ...that we recognize first **any time** -> **anytime**
- 165 s: ...wasn't a little bit **until** -> **till**
- 180 s: ...few people who have **-** -> **gone.**
- 248 s: ...the International Space Station. **-** -> **Space Station.**
- 254 s: ...human science, specifically a **biobrow** -> **Bible**
- 349 s: ...we have a couple **-** -> **of**
- 407 s: ...makes it very, very **important. It's very** -> **-**
- 440 s: ...all of your food. **I'm very excited** -> **-**
- 474 s: ...Russian colleagues there now? **-** -> **On board the space station, I think**
- 474 s: ...now? We have a **-** -> **very**
- 497 s: ...that is our mission **-** -> **of**
- 510 s: ...the International Space Station. **Godspeed.** -> **Godspeak.**
- 516 s: ...Station, this is Houston **ACR.** -> **ASACR.**
- 524 s: ...Station. Please stand by **while** -> **-**
- 524 s: ...stand by while we **configure** -> **can figure**

### Where deepdml/faster-whisper-large-v3-turbo-ct2 hears otherwise (Systran/faster-whisper-large-v3 -> deepdml/faster-whisper-large-v3-turbo-ct2)

- 85 s: ...training, it is really **an** -> **-**
- 86 s: ...is really an overwhelming **-** -> **a**
- 118 s: ...that we recognize first **any time** -> **anytime**
- 165 s: ...wasn't a little bit **until** -> **till**
- 254 s: ...human science, specifically a **biobrow** -> **BIBO**
- 319 s: ...Absolutely. I think that **-** -> **that**
- 384 s: ...concept that Earth is **-** -> **is**
- 406 s: ...it makes it very, **very important. It's** -> **-**
- 440 s: ...all of your food. **I'm very excited** -> **-**
- 474 s: ...Russian colleagues there now? **-** -> **On board the space station, I think**
- 474 s: ...now? We have a **-** -> **very**
- 497 s: ...that is our mission **-** -> **of**
- 524 s: ...Station. Please stand by **while** -> **-**
