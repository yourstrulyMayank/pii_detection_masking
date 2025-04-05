import re
import spacy
import cv2

def string_tokenizer(text):
    final_word_list = []
    words_list = text.replace(" ", "\n").split("\n")

    for element in words_list:
        if len(element) >= 2:
            final_word_list.append(element)

    return final_word_list


def get_regexes():
    rules = {
        "PAN Number": {
            "regex": r"[A-Z]{5}[0-9]{4}[A-Z]{1}"
        }
    }
    return rules

def compile_patterns(patterns):
    if isinstance(patterns, list):
        return [re.compile(pattern) for pattern in patterns]
    else:
        return [re.compile(patterns)]

def custom_pii(text, rules):
    results = []
    all_regexes = {key: re.compile(rule["regex"]) for key, rule in rules.items() if rule["regex"]}

    for key, pattern in all_regexes.items():
        matches = pattern.findall(text)
        if matches:
            results.append({'identifier_class': key, 'result': list(set(matches))})

    return results

def search_pii(text, rules):
    identifiers = custom_pii(text, rules)
    result = {
        "custom PII": identifiers
    }
    return result

def redact_pii(text, labels, model):
    # Load SpaCy’s NLP model for named entity recognition
    nlp = spacy.load('en_core_web_sm')

    # Process the input text
    doc = nlp(text)

    # Define PII categories and their labels
    pii_labels = {
        'SSN': 'social security number',
        'PHONE_NUMBER': 'phone number',
        'PAN Number': 'PAN number'
    }

    # Initialize the redacted text
    redacted_text = text

    # Extract entities from SpaCy
    pii_entities_spacy = [(ent.text, ent.label_) for ent in doc.ents if ent.label_ in pii_labels.keys()]

    
    entities = model.predict_entities(text, labels)
    pii_entities_gliner = [(entity["text"], entity["label"]) for entity in entities]

    # Custom regex entities
    regex_result = search_pii(text, get_regexes())
    pii_entities_regex = []
    
    # Extract and map regex PII entities
    for item in regex_result['custom PII']:
        identifier_class = item['identifier_class']
        if identifier_class in pii_labels:
            for result in item['result']:
                pii_entities_regex.append((result, pii_labels[identifier_class]))

    # Combine entities from SpaCy, GLiNER model, and regex
    pii_entities = set(pii_entities_spacy + pii_entities_gliner + pii_entities_regex)

    # Replace each entity with its label in the format <{label}>
    for ent_text, ent_label in pii_entities:
        if ent_text in redacted_text:
            # Find the appropriate label for replacement
            label = pii_labels.get(ent_label, ent_label)
            redacted_text = redacted_text.replace(ent_text, f'<{label}>')

    return redacted_text

def identify_pii(text, labels, model):
    nlp = spacy.load('en_core_web_sm')
    doc = nlp(text)
    pii_labels = {
        'SSN': 'social security number',
        'PHONE_NUMBER': 'phone number',
        'PAN Number': 'PAN number',
        "Passport Number": 'Passport number'
    }

    pii_entities_spacy = [(ent.text, ent.label_) for ent in doc.ents if ent.label_ in pii_labels.keys()]
    entities = model.predict_entities(text, labels)
    pii_entities_gliner = [(entity["text"], entity["label"]) for entity in entities]

    regex_result = search_pii(text, get_regexes())
    pii_entities_regex = []
    for item in regex_result['custom PII']:
        identifier_class = item['identifier_class']
        if identifier_class in pii_labels:
            for result in item['result']:
                pii_entities_regex.append((result, pii_labels[identifier_class]))

    pii_entities = set(pii_entities_spacy + pii_entities_gliner + pii_entities_regex)
    return pii_entities

# Function to draw black rectangles over detected PII in the image
def draw_black_rectangles(image, detections, labels, model):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    tolerance = 0.05  # 10% tolerance

    for detection in detections:
        coordinates, text, confidence = detection
        top_left = (int(coordinates[0][0]), int(coordinates[0][1]))
        bottom_right = (int(coordinates[2][0]), int(coordinates[2][1]))

        pii_entities = identify_pii(text, labels, model)
        if pii_entities:
            for entity, entity_type in pii_entities:
                entity_start = text.find(entity)
                entity_end = entity_start + len(entity)

                entity_start_fraction = entity_start / len(text)
                entity_end_fraction = entity_end / len(text)

                entity_start_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_start_fraction)
                entity_end_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_end_fraction)

                entity_start_x = max(top_left[0], int(entity_start_x - (bottom_right[0] - top_left[0]) * tolerance))
                entity_end_x = min(bottom_right[0], int(entity_end_x + (bottom_right[0] - top_left[0]) * tolerance))

                cv2.rectangle(image, (entity_start_x, top_left[1]), (entity_end_x, bottom_right[1]), (0, 0, 0), thickness=-1)