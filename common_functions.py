import json
import spacy
import cv2
import ast
import re
# Load SpaCy
nlp = spacy.load('en_core_web_sm')


def load_definitions(file_path="definitions.json"):
    with open(file_path, "r") as file:
        return json.load(file)

import re
import ast

import json
import re
import json
import re

def detect_pii_with_llm(text, labels, definitions, llm_model):
    # Build instructions only for provided labels
    instructions = []
    for label in labels:
        if label in definitions:
            instructions.append(f"{label}: {definitions[label]['description']}")
        else:
            instructions.append(f"Find all instances of {label} in the text.")

    # Final instruction block
    instruction_text = "You are a PII extraction model. Identify and label the following types of PII:\n"
    instruction_text += "\n".join(instructions)

    # Construct prompt (single string)
    prompt = (
        f"{instruction_text}\n\n"
        f"Text:\n{text}\n\n"
        'Return only a valid JSON dictionary of the format:\n'
        '{"label1": ["value1", "value2"], "label2": ["value3"]}\n'
        "Do not include code, explanation, or any other text. Just the dictionary."
    )

    print(prompt)

    try:
        # Call the LLM
        response = llm_model.invoke(prompt)

        # Handle different return formats
        if isinstance(response, str):
            response_text = response
        elif hasattr(response, "content"):
            response_text = response.content
        else:
            response_text = str(response)

        print("LLM raw response:\n", response_text)

        # Sanity check
        if "def " in response_text or "import " in response_text:
            raise ValueError("LLM returned code instead of JSON")

        # Extract JSON object using regex
        match = re.search(r"{\s*.*?}", response_text, re.DOTALL)
        if not match:
            raise ValueError("No valid JSON dictionary found in LLM response")

        json_str = match.group(0)
        result_dict = json.loads(json_str)

    except Exception as e:
        print("Failed to parse LLM response:", e)
        result_dict = {}

    # Convert dict to list of (text, label) tuples
    # result = []
    # for label, values in result_dict.items():
    #     if isinstance(values, list):
    #         for val in values:
    #             result.append((val, label))

    # Convert to list of (text, label) tuples, making sure all values are strings
    result = [
        (str(entity_text), label)
        for label, entities in result_dict.items()
        if isinstance(entities, list)
        for entity_text in entities
        if isinstance(entity_text, (str, int, float))
    ]

    return result



# def detect_pii_with_llm(text, labels, definitions, llm_model):
#     instructions = [f"Find all instances of {label} in the text." for label in labels]
#     for key, val in definitions.items():
#         instructions.append(f"Find all {key}: {val['description']}")

#     prompt = "\n".join(instructions) + f"\n\nText:\n{text}\n\nReturn format:"+ " [{'text': '...', 'label': '...'}]"

#     try:
#         # For LangChain OllamaLLM
#         response = llm_model.invoke(prompt)

#         # In case it's wrapped or raw text
#         if isinstance(response, str):
#             response_text = response
#         elif hasattr(response, 'content'):
#             response_text = response.content
#         else:
#             response_text = str(response)

#         result_str = response_text[response_text.find('['):response_text.rfind(']')+1]
#         result = ast.literal_eval(result_str)
#         # result = eval(result_str)  # WARNING: Use ast.literal_eval if possible for safety

#     except Exception as e:
#         print("Failed to parse LLM response:", e)
#         result = []

#     return [(entity['text'], entity['label']) for entity in result if 'text' in entity and 'label' in entity]


def identify_pii(text, labels, gliner_model, llm_model):
    definitions = load_definitions()

    pii_entities_spacy = [(ent.text, ent.label_) for ent in nlp(text).ents if ent.label_ in labels]

    gliner_entities = gliner_model.predict_entities(text, labels)
    pii_entities_gliner = [(entity["text"], entity["label"]) for entity in gliner_entities]

    pii_entities_llm = detect_pii_with_llm(text, labels, definitions, llm_model)

    pii_entities = set(pii_entities_spacy + pii_entities_gliner + pii_entities_llm)
    return pii_entities


def redact_pii(text, labels, gliner_model, llm_model):
    redacted_text = text
    pii_entities = identify_pii(text, labels, gliner_model, llm_model)

    for ent_text, ent_label in pii_entities:
        redacted_text = redacted_text.replace(ent_text, f"<{ent_label}>")

    return redacted_text


# def draw_black_rectangles(image, detections, labels, gliner_model, llm_model):
#     font = cv2.FONT_HERSHEY_SIMPLEX
#     thickness = 1
#     tolerance = 0.05

#     for detection in detections:
#         coordinates, text, confidence = detection
#         top_left = (int(coordinates[0][0]), int(coordinates[0][1]))
#         bottom_right = (int(coordinates[2][0]), int(coordinates[2][1]))

#         pii_entities = identify_pii(text, labels, gliner_model, llm_model)
#         if pii_entities:
#             for entity, entity_type in pii_entities:
#                 entity_start = text.find(entity)
#                 entity_end = entity_start + len(entity)

#                 entity_start_fraction = entity_start / len(text)
#                 entity_end_fraction = entity_end / len(text)

#                 entity_start_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_start_fraction)
#                 entity_end_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_end_fraction)

#                 entity_start_x = max(top_left[0], int(entity_start_x - (bottom_right[0] - top_left[0]) * tolerance))
#                 entity_end_x = min(bottom_right[0], int(entity_end_x + (bottom_right[0] - top_left[0]) * tolerance))

#                 cv2.rectangle(image, (entity_start_x, top_left[1]), (entity_end_x, bottom_right[1]), (0, 0, 0), thickness=-1)



def draw_black_rectangles(image, detections, labels, gliner_model, llm_model):
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    tolerance = 0.05

    # Combine all text into one string for LLM-based PII detection
    full_text = " ".join([d[1] for d in detections])
    pii_entities = identify_pii(full_text, labels, gliner_model, llm_model)

    for detection in detections:
        coordinates, text, confidence = detection
        top_left = (int(coordinates[0][0]), int(coordinates[0][1]))
        bottom_right = (int(coordinates[2][0]), int(coordinates[2][1]))

        for pii_text, pii_label in pii_entities:
            if pii_text in text:
                entity_start = text.find(pii_text)
                entity_end = entity_start + len(pii_text)

                entity_start_fraction = entity_start / len(text)
                entity_end_fraction = entity_end / len(text)

                entity_start_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_start_fraction)
                entity_end_x = int(top_left[0] + (bottom_right[0] - top_left[0]) * entity_end_fraction)

                entity_start_x = max(top_left[0], int(entity_start_x - (bottom_right[0] - top_left[0]) * tolerance))
                entity_end_x = min(bottom_right[0], int(entity_end_x + (bottom_right[0] - top_left[0]) * tolerance))

                # Black rectangle over detected PII
                cv2.rectangle(image, (entity_start_x, top_left[1]), (entity_end_x, bottom_right[1]), (0, 0, 0), thickness=-1)
