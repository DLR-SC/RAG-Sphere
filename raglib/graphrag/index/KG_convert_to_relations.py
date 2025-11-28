from typing import (
    Dict,
    List
)

from re import findall, finditer, search, sub

def _get_missing_quotations(identifier, text):
    return [item.start() for item in finditer(identifier, text) if text[item.start()-1] != "\""]

def _check_for_errors(dict_text): 
    all_error_positions = []
    all_error_positions.extend(_get_missing_quotations("From\":", dict_text))
    all_error_positions.extend(_get_missing_quotations("To\":", dict_text))
    all_error_positions.extend(_get_missing_quotations("Relation\":", dict_text))

    text_list = list(dict_text)
    for pos in sorted(all_error_positions, reverse = True):
        text_list.insert(pos, "\",\"")

    return "".join(text_list)

def _split_into_entity_relation_bits(relation_str):
    indexes = [item.start()+3 for item in finditer("\",\"", relation_str)][2::3]
    last_idx = 0
    data_len = len(relation_str)
    triplet_parts = []
    for idx in indexes:
        triplet_parts.append(relation_str[last_idx:-(data_len - idx + 2)])
        last_idx = idx

    triplet_parts.append(relation_str[last_idx:]) 
    return "}, {".join(triplet_parts)

def _check_for_duplicated_keys(data):
    triplet_parts = data.split("}, {")
    keys = ["From", "To", "Relation"]
    parts = []
    for part in triplet_parts:
        key_locations = [[loc for loc in range(len(part)) if part.startswith(key, loc)] for key in keys]
        duplicated_location = sum([loc[1] for loc in key_locations if len(loc) > 1])

        if duplicated_location:
            first_part = part[:duplicated_location]
            second_part = part[duplicated_location:]
            part = first_part + '#' + second_part

        parts.append(part)

    return "}, {".join(parts)

def _try_get_relations(relation_str : str) -> List[Dict]:
    """
    Trys to interpret the relation string as a list of dictionaries.

    Parameters:
    - relation_str (str): the string to interprete

    Returns: A list of dictionaries representing relations or None
    """
    relations = None

    # Replace common special characters
    relation_str = relation_str.translate({
        0x26: "and",
        0xC4: "Ae",
        0xD6: "Oe",
        0xDC: "Ue",
        0xDF: "ss",
        0xE4: "ae",
        0xE9: "e",
        0xF6: "oe",
        0xFC: "ue",
    })

    # Try to evaluate the string as an python object
    try:
        relations = eval(relation_str)
    # Evil magic to fix common errors otherwise
    except:
        cleaned_data = "".join(findall(r'(?<=\{).+?(?=\})', relation_str))
        list_data = "[{\"" + (cleaned_data.replace(":_", "\": \"").replace(",_", "\", \"") + "\"").rstrip("\",") + "}]"
        list_data = _check_for_errors(list_data.replace("\"\"", "\",\""))
        splitted_data = _split_into_entity_relation_bits(list_data)
        prepared_dict_data = _check_for_duplicated_keys(splitted_data)

        try:
            relations = eval(prepared_dict_data)
        except:
            relations = None
    
    return relations