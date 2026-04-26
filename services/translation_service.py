from deep_translator import GoogleTranslator

def do_translate(text, direction):
    try:
        if direction == "fr-en":
            return GoogleTranslator(source='fr', target='en').translate(text)
        else:
            return GoogleTranslator(source='en', target='fr').translate(text)
    except Exception as e:
        print("Translation error:", e)
        return text