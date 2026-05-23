from qgis.core import (
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsProject,
    QgsFields,
    QgsVectorFileWriter
)
from qgis.PyQt.QtCore import QVariant
import os


def export_dissimilarity_to_geopackage(source_layer, features, ref_name, other_name, contributions, output_path):
    """
    Exporte une couche GeoPackage avec les contributions locales de dissimilarité.
    
    Args:
        source_layer: Couche QGIS source (pour la géométrie)
        features: Liste des features filtrées
        ref_name: Nom du champ de référence
        other_name: Nom du champ comparé
        contributions: Dict {fid: contribution_value}
        output_path: Chemin du fichier GeoPackage à créer
    
    Returns:
        bool: True si succès, False si erreur
    """
    try:
        # Créer une nouvelle couche mémoire avec la même géométrie
        geom_type = source_layer.wkbType()
        crs = source_layer.crs()
        
        # Créer les champs
        fields = QgsFields()
        
        # Copier tous les champs originaux
        for field in source_layer.fields():
            fields.append(field)
        
        # Ajouter le champ de contribution locale
        fields.append(QgsField("local_dissimilarity", QVariant.Double))
        
        # Créer la couche mémoire
        mem_layer = QgsVectorLayer(
            f"memory?geometry={QgsVectorLayer.geometryType(source_layer.wkbType())}",
            f"dissimilarity_{ref_name}_vs_{other_name}",
            "memory"
        )
        
        mem_layer.setCrs(crs)
        mem_layer.dataProvider().addAttributes(fields)
        mem_layer.updateFields()
        
        # Ajouter les features avec les contributions
        new_features = []
        feature_id_map = {f.id(): f for f in features}
        
        for feature in features:
            new_feat = QgsFeature(fields)
            
            # Copier la géométrie
            new_feat.setGeometry(feature.geometry())
            
            # Copier tous les attributs
            for i, field in enumerate(source_layer.fields()):
                new_feat.setAttribute(field.name(), feature[field.name()])
            
            # Ajouter la contribution locale
            contribution = contributions.get(feature.id(), 0.0)
            new_feat.setAttribute("local_dissimilarity", contribution)
            
            new_features.append(new_feat)
        
        mem_layer.dataProvider().addFeatures(new_features)
        
        # Exporter en GeoPackage
        error = QgsVectorFileWriter.writeAsVectorFormat(
            mem_layer,
            output_path,
            "utf-8",
            mem_layer.crs(),
            "GPKG"
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            print(f"Erreur d'export: {error[1]}")
            return False
        
        # Charger la couche dans QGIS
        gpkg_layer = QgsVectorLayer(output_path, f"dissimilarity_{ref_name}_vs_{other_name}", "ogr")
        
        if gpkg_layer.isValid():
            QgsProject.instance().addMapLayer(gpkg_layer)
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'export GeoPackage: {str(e)}")
        return False
