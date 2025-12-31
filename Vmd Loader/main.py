import os
import struct
import sys
try:
    _THIS_DIR = os.path.abspath(os.path.dirname(__file__))
except Exception:
    _THIS_DIR = os.path.abspath(os.getcwd())
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
import math
try:
    import unreal
    _HAS_UNREAL = True
except Exception:
    unreal = None
    _HAS_UNREAL = False
from PySide6 import QtWidgets, QtCore, QtGui
from VmdReader import VmdReader, _infer_total_frames
import VmdBoneLoader
import VmdMorphLoader

class VmdViewer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setWindowTitle("Vmd Loader")
        self.resize(650, 500)
        self.setMinimumSize(650, 400)

        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)

        self.vmd_path = None
        self.vmd = None
        self.skeletal_mesh = None
        self.drag_hover = False

        self._morph_target_names = set()

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        self.setStyleSheet("""
            QWidget {
                font-family: "Segoe UI", "Yu Gothic UI", "Meiryo UI", sans-serif;
                font-size: 9pt;
                background-color: #1a1a1a;
                color: #d4d4d4;
            }
            QGroupBox {
                font-weight: 600;
                border: 1px solid #404040;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 6px;
                color: #d4d4d4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                color: #569cd6;
            }
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 6px 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #0d5689;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #666666;
            }
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 3px;
                padding: 5px 8px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border: 1px solid #569cd6;
            }
            QTableWidget {
                border: 1px solid #404040;
                border-radius: 3px;
                background-color: #1e1e1e;
                gridline-color: #333333;
                color: #d4d4d4;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #094771;
                color: white;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #404040;
                font-weight: 600;
            }
            QListWidget {
                border: 1px solid #404040;
                border-radius: 3px;
                background-color: #1e1e1e;
                padding: 2px;
                color: #d4d4d4;
            }
            QListWidget::item {
                padding: 6px;
                border-radius: 2px;
                margin: 1px;
            }
            QListWidget::item:selected {
                background-color: #094771;
                color: white;
            }
            QListWidget::item:hover:!selected {
                background-color: #2a2a2a;
            }
            QTabWidget::pane {
                border: 1px solid #404040;
                border-radius: 4px;
                background-color: #252525;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #1e1e1e;
                color: #FFFFFF;
                padding: 8px 18px;
                margin-right: 2px;
                border: 1px solid #404040;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #252525;
                color: #569cd6;
                border-bottom: 2px solid #569cd6;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2a2a2a;
                color: #b0b0b0;
            }
            QLabel {
                color: #d4d4d4;
            }
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 3px;
                background-color: #1e1e1e;
                text-align: center;
                color: #d4d4d4;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0e639c;
                border-radius: 2px;
            }
        """)

    def _build_ui(self):
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        self.tabs = QtWidgets.QTabWidget()
        outer.addWidget(self.tabs, 1)

        self.tab_info = QtWidgets.QWidget()
        self.tab_bone = QtWidgets.QWidget()
        self.tab_morph = QtWidgets.QWidget()
        self.tabs.addTab(self.tab_info, "情報")
        self.tabs.addTab(self.tab_bone, "ボーン")
        self.tabs.addTab(self.tab_morph, "モーフ")

        self._build_info_tab()
        self._build_bone_tab()
        self._build_morph_tab()

        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        outer.addWidget(self.progress)

    def _build_info_tab(self):
        layout = QtWidgets.QVBoxLayout(self.tab_info)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.grp_vmd = QtWidgets.QGroupBox("基本情報")
        vmd_layout = QtWidgets.QVBoxLayout(self.grp_vmd)
        vmd_layout.setContentsMargins(10, 10, 10, 10)

        self.lb_vmd_file = QtWidgets.QLabel("ファイル名：")
        self.lb_model = QtWidgets.QLabel("モデル名：")
        self.lb_bone_keys = QtWidgets.QLabel("ボーンキー数：")
        self.lb_morph_keys = QtWidgets.QLabel("モーフキー数：")
        
        vmd_layout.addWidget(self.lb_vmd_file)
        vmd_layout.addWidget(self.lb_model)
        vmd_layout.addWidget(self.lb_bone_keys)
        vmd_layout.addWidget(self.lb_morph_keys)

        self.grp_settings = QtWidgets.QGroupBox("インポートオプション")
        set_layout = QtWidgets.QVBoxLayout(self.grp_settings)
        set_layout.setContentsMargins(10, 10, 10, 10)
        set_layout.setSpacing(8)

        mesh_container = QtWidgets.QHBoxLayout()
        mesh_container.setSpacing(8)
        mesh_label = QtWidgets.QLabel("スケルタルメッシュ")
        mesh_label.setMinimumWidth(180)
        self.ed_mesh = QtWidgets.QLineEdit("")
        self.ed_mesh.setReadOnly(True)
        self.btn_pick_mesh = QtWidgets.QPushButton("選択状態を取得")
        self.btn_pick_mesh.clicked.connect(self._on_pick_mesh)
        mesh_container.addWidget(mesh_label)
        mesh_container.addWidget(self.ed_mesh, 1)
        mesh_container.addWidget(self.btn_pick_mesh)

        skeleton_container = QtWidgets.QHBoxLayout()
        skeleton_container.setSpacing(8)
        skeleton_label = QtWidgets.QLabel("スケルトン")
        skeleton_label.setMinimumWidth(180)
        self.ed_skeleton = QtWidgets.QLineEdit("")
        self.ed_skeleton.setReadOnly(True)
        self.btn_auto_skeleton = QtWidgets.QPushButton("自動取得")
        self.btn_auto_skeleton.setEnabled(False)
        skeleton_container.addWidget(skeleton_label)
        skeleton_container.addWidget(self.ed_skeleton, 1)
        skeleton_container.addWidget(self.btn_auto_skeleton)

        folder_container = QtWidgets.QHBoxLayout()
        folder_container.setSpacing(8)
        folder_label = QtWidgets.QLabel("アニメーションシーケンス作成先")
        folder_label.setMinimumWidth(180)
        self.ed_folder = QtWidgets.QLineEdit("")
        self.ed_folder.setReadOnly(True)
        self.btn_pick_folder = QtWidgets.QPushButton("選択状態を取得")
        self.btn_pick_folder.clicked.connect(self._on_pick_folder)
        folder_container.addWidget(folder_label)
        folder_container.addWidget(self.ed_folder, 1)
        folder_container.addWidget(self.btn_pick_folder)

        set_layout.addLayout(mesh_container)
        set_layout.addLayout(skeleton_container)
        set_layout.addLayout(folder_container)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(8)
        self.btn_import = QtWidgets.QPushButton("インポート (.vmd)")
        self.btn_import.setEnabled(False)
        self.btn_import.clicked.connect(self._on_import_clicked)
        btn_row.addWidget(self.btn_import)

        layout.addWidget(self.grp_vmd)
        layout.addWidget(self.grp_settings)
        layout.addLayout(btn_row)
        layout.addStretch(1)

    def _build_bone_tab(self):
        layout = QtWidgets.QHBoxLayout(self.tab_bone)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.lst_bone = QtWidgets.QListWidget()
        self.lst_bone.currentRowChanged.connect(self._on_bone_selected)

        self.tbl_bone = QtWidgets.QTableWidget(0, 3)
        self.tbl_bone.setHorizontalHeaderLabels(["frame", "pos (x, y, z)", "rot (x, y, z, w)"])
        self.tbl_bone.verticalHeader().setVisible(False)
        self.tbl_bone.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_bone.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_bone.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        
        bone_header = self.tbl_bone.horizontalHeader()
        bone_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        bone_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        bone_header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        
        self.tbl_bone.setAlternatingRowColors(True)
        self.tbl_bone.setStyleSheet(self.tbl_bone.styleSheet() + """
            QTableWidget {
                alternate-background-color: #212121;
            }
        """)

        split = QtWidgets.QSplitter()
        split.addWidget(self.lst_bone)
        split.addWidget(self.tbl_bone)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([200, 500])
        layout.addWidget(split)

    def _build_morph_tab(self):
        layout = QtWidgets.QHBoxLayout(self.tab_morph)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.lst_morph = QtWidgets.QListWidget()
        self.lst_morph.currentRowChanged.connect(self._on_morph_selected)

        self.tbl_morph = QtWidgets.QTableWidget(0, 2)
        self.tbl_morph.setHorizontalHeaderLabels(["frame", "value"])
        self.tbl_morph.verticalHeader().setVisible(False)
        self.tbl_morph.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_morph.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_morph.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        
        morph_header = self.tbl_morph.horizontalHeader()
        morph_header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        morph_header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        
        self.tbl_morph.setAlternatingRowColors(True)
        self.tbl_morph.setStyleSheet(self.tbl_morph.styleSheet() + """
            QTableWidget {
                alternate-background-color: #212121;
            }
        """)

        split = QtWidgets.QSplitter()
        split.addWidget(self.lst_morph)
        split.addWidget(self.tbl_morph)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([200, 500])
        layout.addWidget(split)

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls():
            for u in md.urls():
                p = u.toLocalFile()
                if p and p.lower().endswith(".vmd"):
                    self.drag_hover = True
                    self.update()
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.drag_hover = False
        self.update()
        event.accept()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drag_hover:
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.fillRect(self.rect(), QtGui.QColor(14, 99, 156, 100))
            painter.setPen(QtGui.QPen(QtGui.QColor(86, 156, 214), 3, QtCore.Qt.DashLine))
            painter.drawRect(self.rect().adjusted(5, 5, -5, -5))
            
            font = painter.font()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.drawText(self.rect(), QtCore.Qt.AlignCenter, "VMDファイルをドロップ")

    def dropEvent(self, event):
        self.drag_hover = False
        self.update()
        
        md = event.mimeData()
        if not md.hasUrls():
            event.ignore()
            return

        for u in md.urls():
            p = u.toLocalFile()
            if p and p.lower().endswith(".vmd"):
                self.vmd_path = os.path.normpath(p)
                self.vmd = None

                self.progress.setVisible(True)
                self.progress.setValue(0)
                QtWidgets.QApplication.processEvents()
                
                try:
                    self.progress.setValue(10)
                    QtWidgets.QApplication.processEvents()
                    
                    self.vmd = VmdReader.read(self.vmd_path)
                    
                    self.progress.setValue(50)
                    QtWidgets.QApplication.processEvents()
                    
                    bones = self.vmd["bones"]
                    morphs = self.vmd["morphs"]

                    bone_keys_total = sum(len(v) for v in bones.values())
                    morph_keys_total = sum(len(v) for v in morphs.values())

                    self.lb_vmd_file.setText(f"ファイル名: {os.path.basename(self.vmd_path)}")
                    self.lb_model.setText(f"モデル名: {self.vmd.get('model', '-')}")
                    self.lb_bone_keys.setText(f"ボーンキー: {bone_keys_total}")
                    self.lb_morph_keys.setText(f"モーフキー: {morph_keys_total}")

                    self.progress.setValue(70)
                    QtWidgets.QApplication.processEvents()

                    self.lst_bone.clear()
                    for name in self.vmd["bone_order"]:
                        count = len(bones[name])
                        self.lst_bone.addItem(f"{name} [{count}]")

                    self.lst_morph.clear()
                    for name in self.vmd["morph_order"]:
                        count = len(morphs[name])
                        self.lst_morph.addItem(f"{name} [{count}]")

                    self.progress.setValue(90)
                    QtWidgets.QApplication.processEvents()

                    if self.lst_bone.count() > 0:
                        self.lst_bone.setCurrentRow(0)
                    if self.lst_morph.count() > 0:
                        self.lst_morph.setCurrentRow(0)

                    self.progress.setValue(100)
                    QtWidgets.QApplication.processEvents()
                    
                except Exception as e:
                    self.vmd = None
                    self.lb_vmd_file.setText(f"ファイル名: {os.path.basename(self.vmd_path)}")
                    self.lb_model.setText("モデル名:")
                    self.lb_bone_keys.setText("ボーンキー数:")
                    self.lb_morph_keys.setText("モーフキー数:")
                    self.lst_bone.clear()
                    self.lst_morph.clear()
                    self.tbl_bone.setRowCount(0)
                    self.tbl_morph.setRowCount(0)
                    print(f"解析失敗: {e}")
                
                QtCore.QTimer.singleShot(500, lambda: self.progress.setVisible(False))
                event.acceptProposedAction()
                return

        event.ignore()

    def _on_pick_mesh(self):
        if unreal is None:
            print("Unreal環境ではありません。")
            return
        assets = unreal.EditorUtilityLibrary.get_selected_assets()
        mesh = None
        for a in assets:
            try:
                if isinstance(a, unreal.SkeletalMesh):
                    mesh = a
                    break
            except Exception:
                continue
        if mesh is None:
            self.skeletal_mesh = None
            self.ed_mesh.setText("")
            self.ed_skeleton.setText("")
            self.btn_import.setEnabled(False)
            return
        self.skeletal_mesh = mesh
        try:
            self.ed_mesh.setText(mesh.get_path_name())
        except Exception:
            try:
                self.ed_mesh.setText(mesh.get_name())
            except Exception:
                self.ed_mesh.setText("")
        skel = None
        try:
            skel = mesh.get_editor_property("skeleton")
        except Exception:
            skel = None
        if skel is not None:
            try:
                self.ed_skeleton.setText(skel.get_path_name())
            except Exception:
                try:
                    self.ed_skeleton.setText(skel.get_name())
                except Exception:
                    self.ed_skeleton.setText("")
        else:
            self.ed_skeleton.setText("")
        try:
            names = mesh.get_all_morph_target_names()
            self._morph_target_names = set(str(n) for n in names)
        except Exception:
            self._morph_target_names = set()
        self.btn_import.setEnabled(self.vmd is not None)

    def _on_pick_folder(self):
        if unreal is None:
            print("Unreal環境ではありません。")
            return
        folder = None
        try:
            folder = unreal.EditorUtilityLibrary.get_current_content_browser_path()
        except Exception:
            folder = None
        if not folder:
            folder = "/Game"
        self.ed_folder.setText(str(folder))

    def _on_import_clicked(self):
        if unreal is None:
            print("Unreal環境ではありません。")
            return
        if self.vmd is None or self.vmd_path is None:
            return
        if self.skeletal_mesh is None:
            return
        folder = self.ed_folder.text().strip()
        if not folder:
            folder = "/Game"
        skeleton = None
        try:
            skeleton = self.skeletal_mesh.get_editor_property("skeleton")
        except Exception:
            skeleton = None
        if skeleton is None:
            return

        self.btn_import.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        QtWidgets.QApplication.processEvents()

        base_name = os.path.splitext(os.path.basename(self.vmd_path))[0]
        asset_name = f"{base_name}_Anim"
        asset_path = f"{folder}/{asset_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            i = 1
            while True:
                asset_name = f"{base_name}_Anim_{i:02d}"
                asset_path = f"{folder}/{asset_name}"
                if not unreal.EditorAssetLibrary.does_asset_exist(asset_path):
                    break
                i += 1

        factory = unreal.AnimSequenceFactory()
        try:
            factory.target_skeleton = skeleton
        except Exception:
            try:
                factory.set_editor_property("target_skeleton", skeleton)
            except Exception:
                pass
        try:
            factory.preview_skeletal_mesh = self.skeletal_mesh
        except Exception:
            try:
                factory.set_editor_property("preview_skeletal_mesh", self.skeletal_mesh)
            except Exception:
                pass

        anim_seq = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=asset_name,
            package_path=folder,
            asset_class=unreal.AnimSequence,
            factory=factory,
        )
        if anim_seq is None:
            self.progress.setVisible(False)
            self.btn_import.setEnabled(True)
            return

        try:
            anim_seq.set_editor_property("interpolation", unreal.AnimInterpolationType.LINEAR)
        except Exception:
            pass

        fps = 30
        num_frames = _infer_total_frames(self.vmd)
        ctrl = anim_seq.get_editor_property("controller")
        ctrl.open_bracket("VMDモーフ取り込み", False)
        try:
            try:
                ctrl.set_frame_rate(unreal.FrameRate(fps, 1), False)
            except Exception:
                pass
            try:
                ctrl.set_number_of_frames(unreal.FrameNumber(num_frames), False)
            except Exception:
                try:
                    ctrl.set_number_of_frames(num_frames, False)
                except Exception:
                    pass

            bones = self.vmd.get("bones", {}) or {}
            if bones:
                self.progress.setValue(10)
                QtWidgets.QApplication.processEvents()
                VmdBoneLoader.apply_bones(ctrl, bones, fps, num_frames, self.skeletal_mesh)

                self.progress.setValue(50)
                QtWidgets.QApplication.processEvents()

            if not self._morph_target_names:
                try:
                    self._morph_target_names = set(str(n) for n in self.skeletal_mesh.get_all_morph_target_names())
                except Exception:
                    self._morph_target_names = set()

            morphs = self.vmd["morphs"]

            VmdMorphLoader.apply_morphs(ctrl, morphs, skeleton, self._morph_target_names, fps)

        finally:
            try:
                ctrl.close_bracket(False)
            except Exception:
                pass

        try:
            unreal.EditorAssetLibrary.save_loaded_asset(anim_seq)
        except Exception:
            pass

        self.progress.setValue(100)
        QtWidgets.QApplication.processEvents()
        QtCore.QTimer.singleShot(500, lambda: self.progress.setVisible(False))
        self.btn_import.setEnabled(True)

    def _on_bone_selected(self, row: int):
        self.tbl_bone.setRowCount(0)
        if self.vmd is None or row < 0:
            return
        item = self.lst_bone.item(row).text()
        name = item.rsplit(" [", 1)[0]
        keys = self.vmd["bones"].get(name, [])

        self.tbl_bone.setRowCount(len(keys))
        for i, key in enumerate(keys):
            frame = key[0]
            pos = key[1]
            rot = key[2]
            it0 = QtWidgets.QTableWidgetItem(f"{frame}")
            it1 = QtWidgets.QTableWidgetItem(f"{pos[0]:.4f}, {pos[1]:.4f}, {pos[2]:.4f}")
            it2 = QtWidgets.QTableWidgetItem(f"{rot[0]:.4f}, {rot[1]:.4f}, {rot[2]:.4f}, {rot[3]:.4f}")
            
            it0.setTextAlignment(QtCore.Qt.AlignCenter)
            it1.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            it2.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            
            self.tbl_bone.setItem(i, 0, it0)
            self.tbl_bone.setItem(i, 1, it1)
            self.tbl_bone.setItem(i, 2, it2)

        table_width = self.tbl_bone.viewport().width()
        self.tbl_bone.setColumnWidth(0, int(table_width * 0.15))

    def _on_morph_selected(self, row: int):
        self.tbl_morph.setRowCount(0)
        if self.vmd is None or row < 0:
            return
        item = self.lst_morph.item(row).text()
        name = item.rsplit(" [", 1)[0]
        keys = self.vmd["morphs"].get(name, [])

        self.tbl_morph.setRowCount(len(keys))
        for i, (frame, w) in enumerate(keys):
            it0 = QtWidgets.QTableWidgetItem(f"{frame}")
            it1 = QtWidgets.QTableWidgetItem(f"{float(w):.4f}")
            
            it0.setTextAlignment(QtCore.Qt.AlignCenter)
            it1.setTextAlignment(QtCore.Qt.AlignCenter)
            
            self.tbl_morph.setItem(i, 0, it0)
            self.tbl_morph.setItem(i, 1, it1)

        table_width = self.tbl_morph.viewport().width()
        self.tbl_morph.setColumnWidth(0, int(table_width * 0.15))



_pyside_app = None
_pyside_win = None


def show_window():
    global _pyside_app, _pyside_win
    app = QtWidgets.QApplication.instance()
    if app is None:
        _pyside_app = QtWidgets.QApplication(sys.argv)
        app = _pyside_app
    if _pyside_win is None:
        _pyside_win = VmdViewer()
    _pyside_win.show()
    _pyside_win.raise_()
    _pyside_win.activateWindow()
    return _pyside_win

if __name__ == "__main__":
    if _HAS_UNREAL:
        show_window()
    else:
        app = QtWidgets.QApplication(sys.argv)
        window = VmdViewer()
        window.show()
        sys.exit(app.exec())