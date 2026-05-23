from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject
from qgis.gui import QgsExpressionBuilderDialog

import csv

from .calculations import (
    dissimilarity_index,
    dissimilarity_index_local,
    interpret_dissimilarity,
    dissimilarity_summary,
    get_filtered_features,
    field_names,
    numeric_field_names
)
from .export_layer import export_dissimilarity_to_geopackage


class SegregationDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Indice de dissimilarité - nationalités")
        self.resize(1000, 750)

        self.layers = []
        self.checkboxes = []
        self.current_calculations = {}  # Stocker les résultats pour l'export

        main = QVBoxLayout(self)

        # ================= PARAMÈTRES
        params = QGroupBox("Paramètres")
        p_layout = QVBoxLayout(params)

        self.layer_combo = QComboBox()
        self.ref_combo = QComboBox()
        self.total_combo = QComboBox()
        self.filter_edit = QLineEdit()

        self.expr_display = QLineEdit()
        self.expr_display.setReadOnly(True)

        p_layout.addWidget(QLabel("Couche"))
        p_layout.addWidget(self.layer_combo)

        p_layout.addWidget(QLabel("Groupe de référence"))
        p_layout.addWidget(self.ref_combo)

        p_layout.addWidget(QLabel("Population totale"))
        p_layout.addWidget(self.total_combo)

        p_layout.addWidget(QLabel("Filtre"))
        p_layout.addWidget(self.filter_edit)

        btn_expr = QPushButton("Expression")
        p_layout.addWidget(btn_expr)
        p_layout.addWidget(self.expr_display)

        main.addWidget(params)

        # ================= GROUPES
        groups_box = QGroupBox("Groupes à comparer")
        g_layout = QVBoxLayout(groups_box)

        btn_line = QHBoxLayout()
        self.btn_all = QPushButton("Tout sélectionner")
        self.btn_none = QPushButton("Tout désélectionner")

        btn_line.addWidget(self.btn_all)
        btn_line.addWidget(self.btn_none)

        g_layout.addLayout(btn_line)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        container = QWidget()
        self.scroll_layout = QVBoxLayout(container)

        self.scroll.setWidget(container)
        g_layout.addWidget(self.scroll)

        main.addWidget(groups_box)

        # ================= SPLITTER TABLE/REPORT
        splitter = QSplitter(Qt.Orientation.Vertical)

        # TABLE
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Référence", "Autre groupe", "Indice", "%", "Interprétation"]
        )

        self.table.setSortingEnabled(True)

        try:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        except:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.table.horizontalHeader().setStretchLastSection(True)

        splitter.addWidget(self.table)

        # REPORT
        self.report = QTextEdit()
        self.report.setReadOnly(True)

        splitter.addWidget(self.report)

        splitter.setSizes([400, 200])

        main.addWidget(splitter)

        # ================= BOUTONS
        btn_row = QHBoxLayout()

        self.btn_calc = QPushButton("Calculer")
        self.btn_export_csv = QPushButton("Exporter CSV")
        self.btn_export_geopackage = QPushButton("Exporter GeoPackage")

        btn_row.addWidget(self.btn_calc)
        btn_row.addWidget(self.btn_export_csv)
        btn_row.addWidget(self.btn_export_geopackage)

        main.addLayout(btn_row)

        # ================= CONNECTIONS
        self.layer_combo.currentIndexChanged.connect(self.refresh_fields)
        self.btn_calc.clicked.connect(self.calculate)
        self.btn_export_csv.clicked.connect(self.export_csv)
        self.btn_export_geopackage.clicked.connect(self.export_geopackage)
        btn_expr.clicked.connect(self.open_expression)

        self.btn_all.clicked.connect(self.select_all)
        self.btn_none.clicked.connect(self.select_none)

        self.load_layers()

    # ===============================
    def load_layers(self):
        self.layers = [
            l for l in QgsProject.instance().mapLayers().values()
            if l.type() == 0
        ]

        self.layer_combo.clear()
        for l in self.layers:
            self.layer_combo.addItem(l.name())

        self.refresh_fields()

    # ===============================
    def refresh_fields(self):

        if not self.layers:
            return

        layer = self.layers[self.layer_combo.currentIndex()]
        self.current_layer = layer

        self.ref_combo.clear()
        self.total_combo.clear()

        fields = field_names(layer)
        numeric = numeric_field_names(layer)

        self.ref_combo.addItems(fields)
        self.total_combo.addItems(numeric if numeric else fields)

        # nettoyer checkboxes
        for i in reversed(range(self.scroll_layout.count())):
            w = self.scroll_layout.takeAt(i).widget()
            if w:
                w.deleteLater()

        self.checkboxes = []

        # seulement champs numériques pertinents
        for f in numeric:
            cb = QCheckBox(f)
            cb.setChecked(True)
            self.scroll_layout.addWidget(cb)
            self.checkboxes.append(cb)

    # ===============================
    def open_expression(self):
        dlg = QgsExpressionBuilderDialog(self.current_layer)
        if dlg.exec():
            self.expr_display.setText(dlg.expressionText())

    # ===============================
    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def select_none(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

    # ===============================
    def get_selected(self):
        return [cb.text() for cb in self.checkboxes if cb.isChecked()]

    # ===============================
    def calculate(self):

        feats = get_filtered_features(
            self.current_layer,
            self.filter_edit.text()
        )

        ref = self.ref_combo.currentText()

        rows = []
        self.current_calculations = {}

        for g in self.get_selected():

            if g == ref:
                continue

            try:
                d, _, _ = dissimilarity_index(
                    self.current_layer,
                    feats,
                    ref,
                    g
                )

                # ignorer résultats inutiles
                if d == 0:
                    continue

                # Calculer les contributions locales
                contributions = dissimilarity_index_local(feats, ref, g)
                
                rows.append((ref, g, d, d * 100, interpret_dissimilarity(d)))
                
                # Stocker les contributions pour l'export
                self.current_calculations[(ref, g)] = {
                    'features': feats,
                    'contributions': contributions,
                    'dissimilarity': d
                }

            except:
                continue

        rows.sort(key=lambda x: x[2], reverse=True)

        self.populate(rows)

        # rapport
        txt = [f"Référence : {ref}", ""]
        for a, b, d, pct, lab in rows:
            txt.append(f"{b} → {d:.4f} ({lab})")

        self.report.setText("\n".join(txt))

    # ===============================
    def populate(self, rows):

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for row in rows:

            r = self.table.rowCount()
            self.table.insertRow(r)

            vals = [
                row[0],
                row[1],
                f"{row[2]:.6f}",
                f"{row[3]:.2f}",
                row[4]
            ]

            for c, v in enumerate(vals):

                item = QTableWidgetItem(v)

                if c in (2, 3):
                    try:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
                    except:
                        item.setTextAlignment(Qt.AlignRight)

                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(True)
        self.table.resizeColumnsToContents()

    # ===============================
    def export_csv(self):

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter CSV",
            "",
            "CSV (*.csv)"
        )

        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            headers = [
                self.table.horizontalHeaderItem(i).text()
                for i in range(self.table.columnCount())
            ]
            writer.writerow(headers)

            for r in range(self.table.rowCount()):
                row = [
                    self.table.item(r, c).text()
                    for c in range(self.table.columnCount())
                ]
                writer.writerow(row)

    # ===============================
    def export_geopackage(self):
        """Exporte une couche GeoPackage avec les contributions locales de dissimilarité."""
        
        if not self.current_calculations:
            QMessageBox.warning(
                self,
                "Avertissement",
                "Veuillez d'abord calculer les indices."
            )
            return

        # Dialogue pour sélectionner le couple de variables
        items = [f"{ref} vs {other}" for ref, other in self.current_calculations.keys()]
        
        item, ok = QInputDialog.getItem(
            self,
            "Sélectionner le couple",
            "Choisissez le couple de variables à exporter:",
            items,
            0,
            False
        )

        if not ok or not item:
            return

        # Parser la sélection
        parts = item.split(" vs ")
        ref_name = parts[0]
        other_name = parts[1]
        
        calc_data = self.current_calculations[(ref_name, other_name)]

        # Dialogue de sauvegarde
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter GeoPackage",
            f"dissimilarity_{ref_name}_vs_{other_name}.gpkg",
            "GeoPackage (*.gpkg)"
        )

        if not path:
            return

        try:
            result = export_dissimilarity_to_geopackage(
                self.current_layer,
                calc_data['features'],
                ref_name,
                other_name,
                calc_data['contributions'],
                path
            )

            if result:
                QMessageBox.information(
                    self,
                    "Succès",
                    f"Couche GeoPackage exportée avec succès!\n\nChamp 'local_dissimilarity' contient la contribution locale de chaque entité."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    "Erreur lors de l'export du GeoPackage."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'export:\n{str(e)}"
            )
