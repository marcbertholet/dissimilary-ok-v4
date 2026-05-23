from qgis.core import QgsFeatureRequest


def safe_float(val):
    try:
        if val in (None, ""):
            return 0.0
        return float(val)
    except:
        return 0.0


def get_filtered_features(layer, filter_expression=None):
    if filter_expression:
        try:
            req = QgsFeatureRequest().setFilterExpression(filter_expression)
            return list(layer.getFeatures(req))
        except:
            return []
    return list(layer.getFeatures())


def dissimilarity_index(layer, features, ref_name, other_name):

    ref_values = [safe_float(f[ref_name]) for f in features]
    other_values = [safe_float(f[other_name]) for f in features]

    Xa = sum(ref_values)
    Xb = sum(other_values)

    if Xa == 0 or Xb == 0:
        return 0.0, [], {}

    D = 0.0

    for a, b in zip(ref_values, other_values):
        D += 0.5 * abs((a / Xa) - (b / Xb))

    return D, [], {}


def dissimilarity_index_local(features, ref_name, other_name):
    """
    Calcule la contribution locale de chaque entité à l'indice de dissimilarité.
    
    Pour chaque entité, calcule: 0.5 * |a/Xa - b/Xb|
    
    Args:
        features: Liste des features
        ref_name: Nom du champ de référence
        other_name: Nom du champ comparé
    
    Returns:
        dict: {fid: contribution_value}
    """
    ref_values = [safe_float(f[ref_name]) for f in features]
    other_values = [safe_float(f[other_name]) for f in features]

    Xa = sum(ref_values)
    Xb = sum(other_values)

    if Xa == 0 or Xb == 0:
        return {}

    contributions = {}

    for feature, a, b in zip(features, ref_values, other_values):
        contribution = 0.5 * abs((a / Xa) - (b / Xb))
        contributions[feature.id()] = contribution

    return contributions


def interpret_dissimilarity(d):
    if d < 0.2:
        return "faible"
    elif d < 0.4:
        return "modérée"
    elif d < 0.6:
        return "forte"
    return "très forte"


def dissimilarity_summary(ref_group, other_group, d):
    level = interpret_dissimilarity(d)
    return f"{level.capitalize()} séparation entre {ref_group} et {other_group}."


def field_names(layer):
    return [f.name() for f in layer.fields()]


def numeric_field_names(layer):
    return [f.name() for f in layer.fields() if f.isNumeric()]
