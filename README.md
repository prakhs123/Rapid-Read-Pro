# Rapid-Read-Pro
## Introduction
This is a Python-based GUI application that converts text to speech, with the ability to play audio, pause, resume, skip, and go back to any part of the audio. It can also display the text word-by-word using the Rapid Serial Visual Presentation (RSVP) technique.

## The Script 
This script enables the conversion of EPUB/PDF files into speech using Azure's Text-to-Speech (TTS) service. The input is first converted into HTML and then transformed into speech using Microsoft Azure Cognitive Services. To run this script, it is necessary to set the SPEECH_KEY and SPEECH_REGION environment variables with a valid Azure subscription key and region, respectively.

Once the input is converted into HTML, the HTML content is divided into multiple ssml strings (XML), which are referred to as "Index." Each ssml string contains headings or paragraphs, which are further divided into smaller units called "tokens." The HTML page can be split into ssml strings either by headings or by a specified number of tokens (default 50).

This script not only provides background TTS but also displays the text's words using Rapid Serial Visual Presentation (RSVP) technique, allowing for more efficient reading.

## Prerequisites
1. Azure subscription - Create one for [free](https://azure.microsoft.com/free/cognitive-services)
2. [Create a Speech resource](https://portal.azure.com/#create/Microsoft.CognitiveServicesSpeechServices) in the Azure portal.
3. Get the Speech resource key and region. After your Speech resource is deployed, select Go to resource to view and manage keys. For more information about Cognitive Services resources, see [Get the keys for your resource](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account#get-the-keys-for-your-resource).

## Requirements
* Python 3.x
* Azure Cognitive Services Speech SDK
* just_playback
* Tkinter
* pdfminer.six
* Other necessary Python modules (as listed in requirements.txt)

## How to use
Clone or download the repository.
Install the required packages from the requirements.txt file using pip install -r requirements.txt.
Run the application using python MainApp.py
The application window will open. You can play/pause, resume, go back, or skip to any part of the audio.

Tokens are the smallest unit, and a single SSML string can contain one or more tokens. By properly utilizing num-token and start-index, the project can accurately generate speech output from the HTML page's multiple SSML string and their contained tokens.

## Creating Executable

```commandline
# intel macs build on silicon macs
arch -x86_64 /Library/Frameworks/Python.framework/Versions/3.9/bin/python3.9-intel64 -m venv v14
source v14/bin/activate
arch -x86_64 pip install -r requirements.txt
arch -x86_64 pip install pyinstaller
arch -x86_64 pyinstaller MainApp.py --paths "v16/lib/python3.9/site-packages" --add-binary "v16/lib/python3.9/site-packages/azure/cognitiveservices/speech/libMicrosoft.CognitiveServices.Speech.core.dylib:." --add-data "InputsApp.py:." --add-data "EpubConfigurationApp.py:." --add-data "IndexConfigurationApp.py:." --add-data "ReadingConfigurationApp.py:." --add-data "RapidReadProApp.py:." --add-data "ColorOptions.py:." --add-data "Words.py:." --add-data "v16/lib/python3.9/site-packages/cffi:cffi" --hidden-import=_cffi_backend --osx-bundle-identifier com.prakhs.freelancer.rapid-read-pro --osx-bundle-identifier com.prakhs.freelancer.rapid-read-pro  -D --name rapid-read-pro --windowed --target-architecture x86_64

# windows
pyinstaller MainApp.py --paths "v18\Lib\site-packages" --add-binary "v18\Lib\site-packages\azure\cognitiveservices\speech\Microsoft.CognitiveServices.Speech.core.dll;." --add-data "v18\Lib\site-packages\cffi;cffi" --hidden-import=_cffi_backend --add-data "InputsApp.py;." --add-data "EpubConfigurationApp.py;." --add-data "IndexConfigurationApp.py;." --add-data "ReadingConfigurationApp.py;." --add-data "RapidReadProApp.py;." --add-data "ColorOptions.py;." --add-data "Words.py;." -D --name rapid-read-pro --windowed
```

## Acknowledgements
This script uses Azure's Text-to-Speech service for converting text into speech.
