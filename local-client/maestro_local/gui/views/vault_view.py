"""Cofre de senhas (KeePass) — tela desktop.

Destrava/cria o cofre global, lista e edita entradas, copia usuário/senha para
a área de transferência com auto-limpeza, e trava por inatividade.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.gui.theme import current_theme
from maestro_local.i18n import t as _t
from maestro_local.vault.manager import (
    AUTO_LOCK_SECONDS,
    CLIPBOARD_CLEAR_SECONDS,
    generate_password,
    get_vault_path,
    vault,
)


class EntryDialog(QDialog):
    def __init__(self, parent=None, entry=None, groups=None):
        super().__init__(parent)
        self.setWindowTitle(_t("Entrada") if not entry else entry["title"])
        self.resize(420, 360)
        form = QFormLayout(self)
        self.title = QLineEdit((entry or {}).get("title", ""))
        form.addRow(_t("Título:"), self.title)
        self.username = QLineEdit((entry or {}).get("username", ""))
        form.addRow(_t("Usuário:"), self.username)
        pw_row = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText(_t("(inalterada)") if entry else "")
        pw_row.addWidget(self.password, 1)
        gen = QPushButton(_t("Gerar"))
        gen.clicked.connect(lambda: self.password.setText(generate_password()))
        pw_row.addWidget(gen)
        show = QPushButton("👁")
        show.setCheckable(True)
        show.setFixedWidth(34)
        show.toggled.connect(
            lambda on: self.password.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
        )
        pw_row.addWidget(show)
        form.addRow(_t("Senha:"), pw_row)
        self.url = QLineEdit((entry or {}).get("url", ""))
        form.addRow("URL:", self.url)
        self.group = QComboBox()
        self.group.setEditable(True)
        self.group.addItem("")
        for g in (groups or []):
            self.group.addItem(g)
        self.group.setCurrentText((entry or {}).get("group", ""))
        form.addRow(_t("Grupo:"), self.group)
        self.notes = QTextEdit((entry or {}).get("notes", ""))
        self.notes.setMaximumHeight(70)
        form.addRow(_t("Notas:"), self.notes)
        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton(_t("Cancelar"))
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        save = QPushButton(_t("Salvar"))
        save.clicked.connect(self.accept)
        btns.addWidget(save)
        form.addRow(btns)


class VaultView(QWidget):
    def __init__(self):
        super().__init__()
        self._clip_timer = QTimer(self)
        self._clip_timer.setSingleShot(True)
        self._clip_timer.timeout.connect(self._clear_clipboard)
        self._clip_value = None
        self._lock_timer = QTimer(self)
        self._lock_timer.setInterval(AUTO_LOCK_SECONDS * 1000)
        self._lock_timer.setSingleShot(True)
        self._lock_timer.timeout.connect(self._auto_lock)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(_t("Senhas"))
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()
        self.lock_btn = QPushButton(_t("Travar"))
        self.lock_btn.setProperty("flat", True)
        self.lock_btn.clicked.connect(self._lock)
        header.addWidget(self.lock_btn)
        root.addLayout(header)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("subtitle")
        self.subtitle.setWordWrap(True)
        root.addWidget(self.subtitle)

        # --- Destravar / criar ---
        self.unlock_box = QFrame()
        self.unlock_box.setProperty("class", "card")
        ul = QVBoxLayout(self.unlock_box)
        self.unlock_hint = QLabel("")
        self.unlock_hint.setWordWrap(True)
        ul.addWidget(self.unlock_hint)
        pw_row = QHBoxLayout()
        self.master_input = QLineEdit()
        self.master_input.setEchoMode(QLineEdit.Password)
        self.master_input.setPlaceholderText(_t("Senha-mestra"))
        self.master_input.returnPressed.connect(self._unlock_or_create)
        pw_row.addWidget(self.master_input, 1)
        self.unlock_btn = QPushButton(_t("Destravar"))
        self.unlock_btn.clicked.connect(self._unlock_or_create)
        pw_row.addWidget(self.unlock_btn)
        ul.addLayout(pw_row)
        self.unlock_status = QLabel("")
        self.unlock_status.setObjectName("subtitle")
        ul.addWidget(self.unlock_status)
        root.addWidget(self.unlock_box)

        # --- Cofre destravado ---
        self.vault_box = QWidget()
        vb = QVBoxLayout(self.vault_box)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(8)
        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(_t("Buscar..."))
        self.search.textChanged.connect(self._reload_entries)
        tools.addWidget(self.search, 1)
        add_btn = QPushButton(_t("+ Nova entrada"))
        add_btn.clicked.connect(self._add_entry)
        tools.addWidget(add_btn)
        vb.addLayout(tools)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.scroll.setWidget(self.list_container)
        vb.addWidget(self.scroll, 1)
        root.addWidget(self.vault_box, 1)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        exists = vault.vault_exists()
        unlocked = vault.is_unlocked
        self.unlock_box.setVisible(not unlocked)
        self.vault_box.setVisible(unlocked)
        self.lock_btn.setVisible(unlocked)
        self.subtitle.setText(
            _t("Cofre global compatível com KeePass (.kdbx): {path}").format(path=str(get_vault_path()))
        )
        if not unlocked:
            if exists:
                self.unlock_hint.setText(_t("Digite a senha-mestra para destravar o cofre."))
                self.unlock_btn.setText(_t("Destravar"))
            else:
                self.unlock_hint.setText(
                    _t("Nenhum cofre encontrado. Digite uma senha-mestra para criar um novo cofre.")
                )
                self.unlock_btn.setText(_t("Criar cofre"))
            self.master_input.clear()
            self.unlock_status.setText("")
        else:
            self._reload_entries()
            self._lock_timer.start()

    def _unlock_or_create(self):
        pw = self.master_input.text()
        if not pw:
            self.unlock_status.setText(_t("Informe a senha-mestra."))
            return
        try:
            if vault.vault_exists():
                vault.unlock(pw)
            else:
                vault.create(pw)
        except Exception as e:  # noqa: BLE001
            self.unlock_status.setText(_t("Falha ao abrir: {error}").format(error=e))
            return
        self.master_input.clear()
        self.refresh()

    def _lock(self):
        vault.lock()
        self._clear_clipboard()
        self.refresh()

    def _auto_lock(self):
        if vault.is_unlocked:
            self._lock()

    def _reset_lock_timer(self):
        if vault.is_unlocked:
            self._lock_timer.start()

    def _reload_entries(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not vault.is_unlocked:
            return
        t = current_theme()
        entries = vault.entries(self.search.text().strip())
        if not entries:
            empty = QLabel(_t("Nenhuma entrada. Use '+ Nova entrada'."))
            empty.setStyleSheet(f"color: {t.text_muted}; padding: 20px;")
            self.list_layout.addWidget(empty)
        for e in entries:
            self.list_layout.addWidget(self._entry_row(e, t))
        self.list_layout.addStretch()

    def _entry_row(self, e, t):
        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 8px; }}"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)
        info = QVBoxLayout()
        info.setSpacing(1)
        title = QLabel(e["title"] or _t("(sem título)"))
        title.setStyleSheet(f"font-weight: 600; color: {t.text_primary}; border: none;")
        info.addWidget(title)
        sub = " · ".join(x for x in [e["username"], e["group"]] if x)
        if sub:
            subl = QLabel(sub)
            subl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
            info.addWidget(subl)
        h.addLayout(info, 1)

        if e["username"]:
            cu = QPushButton(_t("Copiar usuário"))
            cu.setProperty("flat", True)
            cu.clicked.connect(lambda _=False, v=e["username"]: self._copy(v, _t("Usuário copiado")))
            h.addWidget(cu)
        cp = QPushButton(_t("Copiar senha"))
        cp.clicked.connect(lambda _=False, u=e["uuid"]: self._copy_password(u))
        h.addWidget(cp)
        ed = QPushButton("✎")
        ed.setProperty("flat", True)
        ed.setFixedWidth(30)
        ed.clicked.connect(lambda _=False, ent=e: self._edit_entry(ent))
        h.addWidget(ed)
        de = QPushButton("✕")
        de.setProperty("flat", True)
        de.setFixedWidth(30)
        de.clicked.connect(lambda _=False, ent=e: self._delete_entry(ent))
        h.addWidget(de)
        return row

    # ---- Ações ----
    def _copy(self, value, msg):
        self._reset_lock_timer()
        QGuiApplication.clipboard().setText(value)
        self._clip_value = value
        self._clip_timer.start(CLIPBOARD_CLEAR_SECONDS * 1000)
        self.subtitle.setText(
            _t("{msg} — a área de transferência será limpa em {s}s.").format(
                msg=msg, s=CLIPBOARD_CLEAR_SECONDS)
        )

    def _copy_password(self, uuid_hex):
        try:
            pw = vault.get_password(uuid_hex)
        except Exception as e:  # noqa: BLE001
            self.subtitle.setText(str(e))
            return
        self._copy(pw, _t("Senha copiada"))

    def _clear_clipboard(self):
        cb = QGuiApplication.clipboard()
        if self._clip_value is not None and cb.text() == self._clip_value:
            cb.clear()
        self._clip_value = None

    def _add_entry(self):
        self._reset_lock_timer()
        dlg = EntryDialog(self, groups=vault.groups())
        if dlg.exec():
            title = dlg.title.text().strip()
            if not title:
                return
            vault.add_entry(
                title, dlg.username.text().strip(), dlg.password.text(),
                url=dlg.url.text().strip(), notes=dlg.notes.toPlainText().strip(),
                group_name=dlg.group.currentText().strip(),
            )
            self._reload_entries()

    def _edit_entry(self, e):
        self._reset_lock_timer()
        dlg = EntryDialog(self, entry=e, groups=vault.groups())
        if dlg.exec():
            vault.update_entry(
                e["uuid"], title=dlg.title.text().strip(),
                username=dlg.username.text().strip(),
                password=dlg.password.text() or None,
                url=dlg.url.text().strip(), notes=dlg.notes.toPlainText().strip(),
            )
            self._reload_entries()

    def _delete_entry(self, e):
        if QMessageBox.question(
            self, _t("Excluir"), _t("Excluir a entrada \"{title}\"?").format(title=e["title"]),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        vault.delete_entry(e["uuid"])
        self._reload_entries()
