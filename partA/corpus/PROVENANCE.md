# Where this corpus came from (A1)

## Source

I used [OPUS-100](https://huggingface.co/datasets/Helsinki-NLP/opus-100) (Zhang et al., 2020) instead of FLORES-200. Not entirely by choice, I ran into access issues pulling FLORES-200 directly and OPUS-100 was reachable through HuggingFace's datasets-server API, so I switched rather than lose time on it. I'm flagging that trade-off up front rather than pretending this is FLORES-200 data, because it isn't, and the difference matters (see the caveats below).

Pulled via:
```
https://datasets-server.huggingface.co/rows?dataset=Helsinki-NLP/opus-100&config=en-{lang}&split=test&offset={o}&length={n}
```

`en-hi` (rows 0-159), `en-ta` (rows 0-139), `en-kn` (rows 0-99 from both test and train, see below), `en-te` (rows 0-159), `en-ml` (rows 0-99).

## What I did to it

The rows come back as `{en, xx}` pairs, already aligned since OPUS-100 is a single bitext rather than something assembled after the fact. I went through them by hand and dropped anything that wasn't a real sentence, menu labels, `.desktop` file keys, bare `%s` format strings, translator credit blocks, that kind of thing. Also dropped near duplicates and anything under about 4 words on either side. NFC normalization gets applied at load time inside the analysis scripts, not baked into these files, which mirrors the one thing `fertility.py` actually gets right (see `RESULTS.md`). No lowercasing, since that's one of the bugs I'm arguing against.

## What's in each file

| lang | n after filtering | file |
|---|---|---|
| English | 68 | `hin.tsv`, first column |
| Hindi | 68 | `hin.tsv` |
| Tamil | 41 | `tam.tsv` |
| Kannada | 8 | `kan.tsv` |
| Telugu | 34 | `tel.tsv` |
| Malayalam | 39 | `mal.tsv` |

Six languages total, four of them Dravidian, the assignment asks for at least two, this covers all four commonly cited ones (Kannada, Tamil, Telugu, Malayalam). Each file is `english<TAB>target`, one pair per line, UTF-8, no header.

## Domain

Mostly film and TV subtitles, some religious text (Quran translation pairs show up a lot in OPUS-100's source corpora), a handful of software strings that survived filtering, and scattered news and blog text. This is a general purpose scraped bitext, not a curated benchmark, nothing like the editorial care that goes into FLORES-200.

## Where this corpus falls short

The honest version: this is subtitle-heavy, dialogue-heavy text, not FLORES-200's Wikipedia and news domain, so don't expect the absolute numbers here to match a FLORES-200 rerun. They'll be in the right ballpark and pointing the right direction, but treat the exact values as provisional until reconfirmed.

The Kannada number is one I'd push back on hardest if I were reviewing this myself. n=8 versus n=68 for Hindi isn't a small imbalance, it's a real gap, and it's not random, the `en-kn` split in OPUS-100 is dominated by GNOME and KDE desktop localization strings rather than actual sentences, in both the test and train splits. I checked both before settling on 8. That's not just a limitation of my corpus, it's actually a finding worth stating: Kannada is meaningfully less represented in general bitext than the other three Dravidian languages here, and any real production eval effort should check corpus quality per language rather than assuming "four Dravidian languages" means comparable data for all four.

The second thing I'd flag, and this one I can actually speak to personally since Telugu is my first language: even after filtering out the obvious junk from `tel.tsv`, a real chunk of what's left still reads like rough machine translation rather than something a person actually wrote. I went through the file line by line and can point to specific examples, one pair translates "I told him how we used to roll with the ladies in high school" into a Telugu sentence with scrambled word order that puts "I" and "we" next to each other in a way that doesn't happen in natural spoken or written Telugu, and another has words run together without proper spacing where a comma or new clause should be. This isn't a filtering failure on my part exactly, it's that OPUS-100's Telugu side of this bitext is itself often low quality, likely machine translated at some point in its history rather than human translated. I left these lines in rather than quietly removing them, because catching this kind of thing requires actually knowing the language, and it's a genuinely different failure mode from Kannada's problem. Kannada's issue is coverage, there isn't enough real sentence data. Telugu's issue is quality, there's plenty of data but a meaningful slice of it isn't trustworthy as ground truth for what "natural Telugu" looks like. Both are real limits on what this corpus can tell you, and I don't think either one shows up unless you either read the language or go looking for it specifically.

Subtitle text also runs shorter and more colloquial than what this assistant will actually produce (structured, longer responses), so I'd treat the tok/word and tok/byte numbers here as directionally solid but not final. And beyond the Telugu spot check above, I didn't independently re-verify alignment for the other languages beyond a quick skim, OPUS-100's automatic alignment has some known noise, and at this sample size I didn't try to catch every misaligned pair in Hindi, Tamil, Kannada, or Malayalam the way I did for Telugu.

## What I'd do next

Rerun `../corrected_analysis.py` against FLORES-200 or FLORES+ (997 professionally translated, multi-parallel sentences per language) for the same six languages, once FLORES access isn't blocked, that removes both the domain mismatch and the translation-quality problem in one move, since FLORES is professionally translated rather than scraped. The scripts only expect a plain `english<TAB>target` TSV per language, so this is a data swap, not a rewrite.
