# Shorts-Content-Generator
This project generates a Youtube shorts fomat video and uploads it to Youtube without any user action.


This is a project that allows users to create a Youtube Shorts form video and automatically upload to Youtube.

How it works:

* First a script is generated using local llama3, previous scripts are given to the model in order to prevent same script generation
* If script is too long for short content, new script is generated
* If script is valid, it is added to the previously generated scripts
* A random background video is choosen from downloaded videos folder, any shorts format video is valid
* Video can be at any lenght, however final product's length will be as long as the speech's lenght, if video is longer, than it is cut, if it is shorter, then it is repeated
* For text to speech generation I have used [FujiwaraChoki's Money Printer](https://github.com/FujiwaraChoki/MoneyPrinter) project. It is a very similar project however that project reqires user inputs and actions. This project is completely automated.
* I have used the tiktokvoice.py from Money Printer project, which uses TikTok's API to generate a speech from given text
* After generating the speech, the script is splitted into chunks, each containing enough characters to fit the screen while containing word integrity
* Using these new chunks and the generated speech, a subtitle file is generated with timestamps
* These subtitles are checked for any errors
* Generated speech and subtitles are added to the selected video and Shorts content is ready
* Using Youtube's API, generated video is uploaded to the youtube (daily limit is around 6-7 videos)
* During this process if any error is encountered, process restarts and new video is generated
* In order to use this, an .env file is required with required api keys and client secrets
