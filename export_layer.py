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
import tempfile


def create_temporary_layer(source_layer, features, ref_name, other_name, contributions):
    """
    Crée une couche temporaire en mémoire avec tous les attributs nécessaires.
    
    Args:
        source_layer: Couche QGIS source (pour la géométrie)
        features: Liste des features filtrées
        ref_name: Nom du champ de référence
        other_name: Nom du champ comparé
        contributions: Dict {fid: contribution_value}
    
    Returns:
        QgsVectorLayer: Couche mémoire avec tous les attributs
    """
    try:
        # Obtenir le type de géométrie et le CRS
        geom_type = source_layer.wkbType()
        crs = source_layer.crs()
        
        # Déterminer le type de géométrie approprié AVANT de créer la couche
        if geom_type == 1:  # Point
            geom_string = "Point"
        elif geom_type == 2:  # LineString
            geom_string = "LineString"
        elif geom_type == 3:  # Polygon
            geom_string = "Polygon"
        else:
            geom_string = "Point"
        
        # Créer les champs
        fields = QgsFields()
        
        # Copier tous les champs originaux
        for field in source_layer.fields():
            fields.append(field)
        
        # Ajouter les champs de contribution et de calcul
        fields.append(QgsField("local_dissimilarity", QVariant.Double))
        fields.append(QgsField(f"contrib_pct", QVariant.Double))
        
        # Créer la couche mémoire avec le bon type de géométrie
        layer_name = f"dissimilarity_{ref_name}_vs_{other_name}"
        mem_layer = QgsVectorLayer(
            f"{geom_string}?crs={crs.authid()}",
            layer_name,
            "memory"
        )
        
        mem_layer.setCrs(crs)
        
        # Ajouter les champs
        provider = mem_layer.dataProvider()
        provider.addAttributes(fields)
        mem_layer.updateFields()
        
        # Ajouter les features avec les contributions
        new_features = []
        total_contribution = sum(contributions.values()) if contributions else 0.0
        
        for feature in features:
            new_feat = QgsFeature(fields)
            
            # Copier la géométrie
            new_feat.setGeometry(feature.geometry())
            
            # Copier tous les attributs
            for field in source_layer.fields():
                new_feat.setAttribute(field.name(), feature[field.name()])
            
            # Ajouter les contributions
            contribution = contributions.get(feature.id(), 0.0)
            new_feat.setAttribute("local_dissimilarity", contribution)
            
            # Calculer le pourcentage de contribution
            if total_contribution > 0:
                contrib_pct = (contribution / total_contribution) * 100.0
            else:
                contrib_pct = 0.0
            new_feat.setAttribute("contrib_pct", contrib_pct)
            
            new_features.append(new_feat)
        
        provider.addFeatures(new_features)
        mem_layer.updateFields()
        
        return mem_layer
        
    except Exception as e:
        print(f"Erreur lors de la création de la couche temporaire: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def export_dissimilarity_to_geopackage(source_layer, features, ref_name, other_name, contributions, output_path):
    """
    Exporte une couche GeoPackage avec les contributions locales de dissimilarité.
    Crée d'abord une couche temporaire dans QGIS, puis l'exporte.
    
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
        # Créer d'abord la couche temporaire
        mem_layer = create_temporary_layer(
            source_layer, 
            features, 
            ref_name, 
            other_name, 
            contributions
        )
        
        if mem_layer is None:
            print("Impossible de créer la couche temporaire")
            return False
        
        # Ajouter la couche temporaire à QGIS
        QgsProject.instance().addMapLayer(mem_layer)
        print(f"Couche temporaire créée: {mem_layer.name()}")
        
        # Exporter en GeoPackage
        error = QgsVectorFileWriter.writeAsVectorFormat(
            mem_layer,
            output_path,
            "utf-8",
            mem_layer.crs(),
            "GPKG"
        )
        
        if error[0] != QgsVectorFileWriter.NoError:
            print(f"Erreur d'export GeoPackage: {error[1]}")
            return False
        
        print(f"GeoPackage exporté avec succès: {output_path}")
        
        # Charger le GeoPackage exporté dans QGIS
        try:
            gpkg_layer = QgsVectorLayer(
                output_path, 
                f"dissimilarity_{ref_name}_vs_{other_name} (exported)", 
                "ogr"
            )
            
            if gpkg_layer.isValid():
                QgsProject.instance().addMapLayer(gpkg_layer)
                print(f"GeoPackage chargé dans QGIS: {gpkg_layer.name()}")
            else:
                print("Le GeoPackage n'a pas pu être chargé")
                return False
                
        except Exception as e:
            print(f"Avertissement: Le GeoPackage n'a pas pu être rechargé: {str(e)}")
            # L'export était réussi, on retourne True quand même
        
        return True
        
    except Exception as e:
        print(f"Erreur lors de l'export GeoPackage: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
