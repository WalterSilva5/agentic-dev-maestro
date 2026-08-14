from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import (
    list_ai_providers,
    load_config,
    save_ai_providers,
    save_config,
)
from maestro_local.gui.theme import current_theme
from maestro_local.gui.no_wheel_combo import NoWheelComboBox
from maestro_local.i18n import t


class ConnTestWorker(QThread):
    done = Signal(bool, str, list)

    def __init__(self, provider):
        super().__init__()
        self._provider = provider

    def run(self):
        from maestro_local.ai.providers import listar_modelos
        ok, msg, modelos = listar_modelos(self._provider)
        self.done.emit(ok, msg, modelos)


class SettingsView(QWidget):
    notification_changed = Signal()
    ai_provider_changed = Signal()

    def __init__(self):
        super().__init__()
        self._loading = False

        # Espera a digitação parar antes de gravar o provedor de IA (ver
        # _on_ai_field_changed). 600 ms: acima do intervalo entre teclas de
        # quem digita rápido, e curto o bastante para não parecer que a
        # configuração não foi salva.
        self._ai_save_timer = QTimer(self)
        self._ai_save_timer.setSingleShot(True)
        self._ai_save_timer.setInterval(600)
        self._ai_save_timer.timeout.connect(self._persistir_provedor_ai)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        title = QLabel(t("Configurações"))
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        subtitle = QLabel(
            t("Configurações gerais da aplicação — pomodoro, notificações e preferências.")
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        main_layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)

        self._build_language_section()
        self._build_ai_section()
        self._build_transcricoes_section()
        self._build_features_section()
        self._build_daily_focus_section()
        self._build_eyecare_section()
        self._build_pomodoro_section()
        self._build_coach_section()
        self._build_notification_section()
        self._build_startup_section()

        self.cards_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        self._load_settings()

    def _make_card(self, icon, title_text):
        card = QFrame()
        card.setProperty("class", "card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)

        badge = QLabel(icon)
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignCenter)
        theme = current_theme()
        badge.setStyleSheet(
            f"background: {theme.accent}; color: {theme.text_on_accent}; "
            f"border-radius: 16px; font-size: 14px; font-weight: 800; border: none;"
        )
        header.addWidget(badge)

        heading = QLabel(title_text)
        heading.setProperty("class", "cardTitle")
        header.addWidget(heading)
        header.addStretch()

        layout.addLayout(header)
        self.cards_layout.addWidget(card)
        return card, layout

    def _build_language_section(self):
        from maestro_local.i18n import SUPPORTED, t
        card, layout = self._make_card("🌐", t("Idioma"))

        desc = QLabel(t("Idioma da interface. Trocar exige reiniciar o aplicativo."))
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(t("Idioma:")))
        self.lang_combo = NoWheelComboBox()
        for code, name in SUPPORTED.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        row.addWidget(self.lang_combo)
        row.addStretch()
        layout.addLayout(row)

    def _on_language_changed(self, _index):
        if self._loading:
            return
        from maestro_local.config import get_language, set_language
        from maestro_local.i18n import t
        code = self.lang_combo.currentData()
        if code == get_language():
            return
        set_language(code)

        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle(t("Idioma"))
        box.setText(t("O idioma foi alterado. Reinicie o aplicativo para aplicar."))
        restart_btn = box.addButton(t("Reiniciar agora"), QMessageBox.AcceptRole)
        box.addButton(t("Depois"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is restart_btn:
            self._restart_app()

    def _restart_app(self):
        import os
        import sys
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
        os.execv(sys.executable, [sys.executable, "-m", "maestro_local", *sys.argv[1:]])

    def _build_ai_section(self):
        card, layout = self._make_card("✦", t("Provedores de IA"))

        desc = QLabel(
            t("Configure provedores compatíveis com OpenAI (LM Studio local, opencode, etc.). "
              "O provedor ativo é usado pelo Chat estratégico.")
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        sel_row = QHBoxLayout()
        sel_row.setSpacing(8)
        sel_row.addWidget(QLabel(t("Provedor ativo:")))
        self.ai_combo = NoWheelComboBox()
        self.ai_combo.currentIndexChanged.connect(self._on_provider_selected)
        sel_row.addWidget(self.ai_combo, 1)
        layout.addLayout(sel_row)

        def field(label_text, placeholder, password=False):
            row = QVBoxLayout()
            row.setSpacing(2)
            row.addWidget(QLabel(label_text))
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            if password:
                edit.setEchoMode(QLineEdit.Password)
            edit.textChanged.connect(self._on_ai_field_changed)
            # Enter ou sair do campo grava na hora, sem esperar a pausa.
            edit.editingFinished.connect(self._persistir_provedor_ai)
            row.addWidget(edit)
            layout.addLayout(row)
            return edit

        self.ai_name = field(t("Nome"), t("Ex: LM Studio local"))
        self.ai_base_url = field("Base URL", "http://localhost:1234/v1")
        self.ai_api_key = field("API Key", t("deixe em branco se local"), password=True)
        self.ai_model = field(t("Modelo"), t("ex: qwen2.5-coder-7b-instruct"))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.ai_test_btn = QPushButton(t("Testar conexão"))
        self.ai_test_btn.setFixedHeight(30)
        self.ai_test_btn.setCursor(Qt.PointingHandCursor)
        self.ai_test_btn.clicked.connect(self._test_ai_connection)
        btn_row.addWidget(self.ai_test_btn)

        self.ai_new_btn = QPushButton(t("Novo provedor"))
        self.ai_new_btn.setFixedHeight(30)
        self.ai_new_btn.setCursor(Qt.PointingHandCursor)
        self.ai_new_btn.clicked.connect(self._new_provider)
        btn_row.addWidget(self.ai_new_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.ai_status = QLabel("")
        self.ai_status.setWordWrap(True)
        self.ai_status.setProperty("class", "hint")
        layout.addWidget(self.ai_status)

    def _current_providers(self):
        from maestro_local.ai.providers import DEFAULT_PROVIDERS, merge_missing_defaults
        providers = list_ai_providers()
        if not providers:
            providers = [dict(p) for p in DEFAULT_PROVIDERS]
            save_ai_providers(providers, active_id=providers[0]["id"])
            return providers
        merged = merge_missing_defaults(providers)
        if len(merged) != len(providers):
            save_ai_providers(merged)
            providers = merged
        return providers

    def _load_ai_section(self):
        self._loading = True
        providers = self._current_providers()
        from maestro_local.config import get_active_ai_provider
        active = get_active_ai_provider()
        active_id = active["id"] if active else providers[0]["id"]

        self.ai_combo.clear()
        for p in providers:
            self.ai_combo.addItem(p["name"], p["id"])
        idx = next((i for i, p in enumerate(providers) if p["id"] == active_id), 0)
        self.ai_combo.setCurrentIndex(idx)
        self._fill_provider_fields(providers[idx])
        self._loading = False

    def _fill_provider_fields(self, p):
        self.ai_name.setText(p.get("name", ""))
        self.ai_base_url.setText(p.get("base_url", ""))
        self.ai_api_key.setText(p.get("api_key", ""))
        self.ai_model.setText(p.get("model", ""))

    def _on_provider_selected(self, index):
        if self._loading or index < 0:
            return
        providers = self._current_providers()
        pid = self.ai_combo.itemData(index)
        from maestro_local.config import set_active_ai_provider
        set_active_ai_provider(pid)
        p = next((x for x in providers if x["id"] == pid), None)
        if p:
            self._loading = True
            self._fill_provider_fields(p)
            self._loading = False
        self.ai_status.setText("")
        self.ai_provider_changed.emit()

    def _on_ai_field_changed(self):
        """Adia a gravação até a digitação parar.

        Gravar a cada tecla salvava o campo pela metade, e como salvar também
        invalida o cache de modelos, a IA passava a ser chamada com o nome
        incompleto: os erros que apareciam eram "Model minim is not supported",
        "Model minimax-m2. is not supported" — prefixos exatos do que estava
        sendo digitado.
        """
        if self._loading:
            return
        self._ai_save_timer.start()

    def _persistir_provedor_ai(self):
        if self._loading:
            return
        self._ai_save_timer.stop()
        providers = self._current_providers()
        pid = self.ai_combo.currentData()
        for p in providers:
            if p["id"] == pid:
                p["name"] = self.ai_name.text().strip() or p["name"]
                p["base_url"] = self.ai_base_url.text().strip()
                p["api_key"] = self.ai_api_key.text().strip()
                p["model"] = self.ai_model.text().strip()
                break
        save_ai_providers(providers, active_id=pid)
        # atualiza o rótulo no combo se o nome mudou
        i = self.ai_combo.currentIndex()
        if i >= 0:
            self._loading = True
            self.ai_combo.setItemText(i, self.ai_name.text().strip() or self.ai_combo.itemText(i))
            self._loading = False
        self.ai_provider_changed.emit()

    def _new_provider(self):
        providers = self._current_providers()
        existing = {p["id"] for p in providers}
        n = 1
        new_id = "custom-1"
        while new_id in existing:
            n += 1
            new_id = f"custom-{n}"
        providers.append({
            "id": new_id, "name": t("Novo provedor {n}").format(n=n),
            "base_url": "http://localhost:1234/v1", "api_key": "", "model": "",
        })
        save_ai_providers(providers, active_id=new_id)
        self._load_ai_section()
        self.ai_provider_changed.emit()

    def _test_ai_connection(self):
        self._persistir_provedor_ai()   # testa o que está na tela, não o antigo
        provider = {
            "base_url": self.ai_base_url.text().strip(),
            "api_key": self.ai_api_key.text().strip(),
            "model": self.ai_model.text().strip(),
        }
        self.ai_status.setText(t("Testando..."))
        self.ai_test_btn.setEnabled(False)
        self._conn_worker = ConnTestWorker(provider)
        self._conn_worker.done.connect(self._on_conn_tested)
        self._conn_worker.start()

    def _on_conn_tested(self, ok, msg, modelos):
        theme = current_theme()
        color = theme.text_secondary if ok else getattr(theme, "danger", "#D32F2F")
        prefix = "✓ " if ok else "✕ "
        self.ai_status.setText(prefix + msg)
        self.ai_status.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.ai_test_btn.setEnabled(True)
        if ok and modelos:
            self._mostrar_modelos(modelos)

    def _mostrar_modelos(self, modelos):
        """Lista o que o provedor respondeu, para copiar ou usar direto.

        Antes só cabiam cinco nomes truncados no rótulo de status — dava para
        ver que a conexão funcionou, mas não para saber como o modelo se chama.
        """
        from maestro_local.gui.model_picker_dialog import ModelPickerDialog
        dlg = ModelPickerDialog(
            self, modelos, self.ai_model.text().strip(),
            provider={"base_url": self.ai_base_url.text().strip(),
                      "api_key": self.ai_api_key.text().strip()})
        if dlg.exec() == QDialog.Accepted and dlg.escolhido:
            self.ai_model.setText(dlg.escolhido)
            # Escolha explícita: grava agora, sem a espera da digitação.
            self._persistir_provedor_ai()

    def _build_transcricoes_section(self):
        card, layout = self._make_card("🎙", t("Reuniões"))

        desc = QLabel(
            t("Modelo do Whisper usado para transcrever gravações localmente. "
              "Modelos maiores são mais precisos, porém mais lentos.")
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(t("Modelo Whisper:")))
        self.whisper_model = NoWheelComboBox()
        from maestro_local.transcricoes.constants import WHISPER_SUPPORTED_MODELS
        self.whisper_model.addItems(WHISPER_SUPPORTED_MODELS)
        self.whisper_model.currentIndexChanged.connect(self._save_settings)
        self.whisper_model.currentIndexChanged.connect(self._update_whisper_ram_hint)
        row.addWidget(self.whisper_model)

        self.whisper_ram_hint = QLabel("")
        self.whisper_ram_hint.setProperty("class", "hint")
        row.addWidget(self.whisper_ram_hint)
        self._update_whisper_ram_hint()

        row.addSpacing(12)
        row.addWidget(QLabel(t("Idioma:")))
        self.whisper_lang = QLineEdit()
        self.whisper_lang.setPlaceholderText(t("pt, en... (vazio = auto)"))
        self.whisper_lang.setFixedWidth(120)
        self.whisper_lang.textChanged.connect(self._save_settings)
        row.addWidget(self.whisper_lang)
        row.addStretch()
        layout.addLayout(row)

    def _update_whisper_ram_hint(self):
        """Mostra a RAM aproximada do modelo selecionado — ajuda a escolher
        conscientemente o trade-off precisão x memória (fica residente após o
        primeiro uso; ver transcriber.release_model para a liberação por ociosidade)."""
        from maestro_local.transcricoes.constants import WHISPER_MODEL_RAM_MB
        model = self.whisper_model.currentText()
        mb = WHISPER_MODEL_RAM_MB.get(model)
        if mb is None:
            self.whisper_ram_hint.setText("")
            return
        text = f"~{mb} MB" if mb < 1000 else f"~{mb / 1000:.1f} GB"
        self.whisper_ram_hint.setText(t("≈ {ram} de RAM enquanto em uso").format(ram=text))

    def _build_features_section(self):
        from maestro_local import features
        card, layout = self._make_card("🧩", t("Funcionalidades"))

        desc = QLabel(
            t("Desligue o que você não usa para deixar a interface mais enxuta. "
              "Nada é apagado — é só deixar de aparecer, e dá para religar aqui "
              "a qualquer momento. Exige reiniciar o aplicativo."))
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.feature_checks = {}
        for grupo, itens in features.por_grupo().items():
            titulo = QLabel(grupo.upper())
            titulo.setObjectName("navSection")
            layout.addWidget(titulo)
            for f in itens:
                chk = QCheckBox(t(f.rotulo))
                if f.descricao:
                    chk.setToolTip(t(f.descricao))
                chk.setChecked(features.habilitada(f.chave))
                chk.toggled.connect(
                    lambda on, chave=f.chave: self._on_feature_toggled(chave, on))
                layout.addWidget(chk)
                self.feature_checks[f.chave] = chk

    def _on_feature_toggled(self, chave: str, ligada: bool):
        if self._loading:
            return
        from maestro_local import features
        features.definir(chave, ligada)

    def _build_daily_focus_section(self):
        card, layout = self._make_card("🎯", t("Foco do dia"))

        desc = QLabel(
            t("Ao abrir o programa, uma vez por dia, mostra esta mensagem com a "
              "lista das suas pendências."))
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.focus_enabled = QCheckBox(t("Mostrar ao abrir o programa"))
        self.focus_enabled.toggled.connect(self._save_settings)
        layout.addWidget(self.focus_enabled)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(t("Mensagem:")))
        self.focus_message = QLineEdit()
        self.focus_message.setPlaceholderText(t("FOCO NO OBJETIVO"))
        self.focus_message.setToolTip(
            t("Aparece em destaque no topo do modal. Vazio volta ao padrão."))
        self.focus_message.textChanged.connect(self._save_settings)
        row.addWidget(self.focus_message, 1)
        layout.addLayout(row)

    def _build_eyecare_section(self):
        card, layout = self._make_card("👁", t("Pausa para os olhos"))

        desc = QLabel(
            t("Lembrete periódico para olhar para longe (regra 20-20-20). "
              "Não aparece enquanto uma reunião está sendo gravada — a pausa "
              "espera terminar em vez de ser perdida. Ligue/desligue em "
              "Funcionalidades."))
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        linha = QHBoxLayout()
        linha.setSpacing(8)
        linha.addWidget(QLabel(t("A cada (min):")))
        self.eye_intervalo = QSpinBox()
        self.eye_intervalo.setRange(5, 180)
        self.eye_intervalo.setFixedWidth(70)
        self.eye_intervalo.valueChanged.connect(self._save_eyecare)
        linha.addWidget(self.eye_intervalo)

        linha.addWidget(QLabel(t("Duração (s):")))
        self.eye_duracao = QSpinBox()
        self.eye_duracao.setRange(5, 300)
        self.eye_duracao.setFixedWidth(70)
        self.eye_duracao.valueChanged.connect(self._save_eyecare)
        linha.addWidget(self.eye_duracao)

        linha.addWidget(QLabel(t("Adiar (min):")))
        self.eye_adiar = QSpinBox()
        self.eye_adiar.setRange(1, 60)
        self.eye_adiar.setFixedWidth(70)
        self.eye_adiar.valueChanged.connect(self._save_eyecare)
        linha.addWidget(self.eye_adiar)
        linha.addStretch()

        # Sem isso só dá para conferir a pausa esperando o intervalo inteiro.
        self.eye_testar = QPushButton(t("Testar agora"))
        self.eye_testar.setProperty("class", "secondary")
        self.eye_testar.setToolTip(
            t("Mostra a pausa imediatamente, sem esperar o intervalo."))
        self.eye_testar.clicked.connect(self._testar_eyecare)
        linha.addWidget(self.eye_testar)
        layout.addLayout(linha)

        atalho = QLabel(
            t("O ícone na bandeja do sistema permite adiar ou fazer a pausa "
              "sem abrir esta tela."))
        atalho.setWordWrap(True)
        atalho.setProperty("class", "hint")
        layout.addWidget(atalho)

    def _testar_eyecare(self):
        janela = self.window()
        if hasattr(janela, "testar_eyecare"):
            janela.testar_eyecare()

    def _save_eyecare(self):
        if self._loading:
            return
        from maestro_local import eyecare
        eyecare.definir(intervalo_min=self.eye_intervalo.value(),
                        duracao_seg=self.eye_duracao.value(),
                        adiar_min=self.eye_adiar.value())

    def _build_pomodoro_section(self):
        card, layout = self._make_card("🍅", t("Pomodoro"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel(t("Duração da sessão (minutos):")))
        self.pomodoro_duration = QSpinBox()
        self.pomodoro_duration.setRange(1, 120)
        self.pomodoro_duration.setValue(25)
        self.pomodoro_duration.setFixedWidth(80)
        self.pomodoro_duration.valueChanged.connect(self._save_settings)
        row.addWidget(self.pomodoro_duration)
        row.addStretch()
        layout.addLayout(row)

    def _build_startup_section(self):
        from maestro_local import autostart
        card, layout = self._make_card("🚀", t("Inicialização"))

        desc = QLabel(
            t("Inicia o Maestro automaticamente ao ligar o computador (no login).")
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.startup_check = QCheckBox(t("Iniciar junto com o computador"))
        if autostart.is_supported():
            self.startup_check.setChecked(autostart.is_enabled())
        else:
            self.startup_check.setEnabled(False)
            self.startup_check.setToolTip(t("Disponível apenas no Linux."))
        # conecta depois de definir o estado, para não disparar ao carregar
        self.startup_check.toggled.connect(self._on_startup_toggled)
        layout.addWidget(self.startup_check)

        self.startup_status = QLabel("")
        self.startup_status.setProperty("class", "hint")
        layout.addWidget(self.startup_status)

    def _on_startup_toggled(self, on):
        from maestro_local import autostart
        try:
            autostart.set_enabled(on)
            self.startup_status.setText(
                t("Ativado — o Maestro abrirá automaticamente no próximo login.")
                if on else t("Desativado — o Maestro não abrirá sozinho.")
            )
        except Exception as e:  # noqa: BLE001
            self.startup_status.setText(t("Erro: {error}").format(error=e))
            # reverte visualmente sem redisparar o sinal
            self.startup_check.blockSignals(True)
            self.startup_check.setChecked(autostart.is_enabled())
            self.startup_check.blockSignals(False)

    def _build_coach_section(self):
        card, layout = self._make_card("💡", t("Coach proativo"))

        desc = QLabel(
            t("O agente dá dicas curtas e acionáveis ao longo do dia, com base no seu "
              "board e TODOs, num card não intrusivo. Requer um provedor de IA ativo.")
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.coach_enabled = QCheckBox(t("Ativar dicas proativas do agente"))
        self.coach_enabled.toggled.connect(self._save_settings)
        layout.addWidget(self.coach_enabled)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(8)
        interval_row.addWidget(QLabel(t("Intervalo (minutos):")))
        self.coach_interval = QSpinBox()
        self.coach_interval.setRange(15, 480)
        self.coach_interval.setValue(90)
        self.coach_interval.setFixedWidth(80)
        self.coach_interval.valueChanged.connect(self._save_settings)
        interval_row.addWidget(self.coach_interval)
        interval_row.addStretch()
        layout.addLayout(interval_row)

    def _build_notification_section(self):
        card, layout = self._make_card("🔔", t("Notificações push"))

        desc = QLabel(
            t("Envia notificações periódicas na área de trabalho com uma mensagem personalizada. "
              "Útil para lembretes de pausas, check-ins ou qualquer lembrete recorrente.")
        )
        desc.setWordWrap(True)
        desc.setProperty("class", "hint")
        layout.addWidget(desc)

        self.notif_enabled = QCheckBox(t("Ativar notificações periódicas"))
        self.notif_enabled.toggled.connect(self._on_notif_toggled)
        layout.addWidget(self.notif_enabled)

        self.notif_settings_frame = QFrame()
        notif_inner = QVBoxLayout(self.notif_settings_frame)
        notif_inner.setContentsMargins(0, 4, 0, 0)
        notif_inner.setSpacing(8)

        interval_row = QHBoxLayout()
        interval_row.setSpacing(8)
        interval_row.addWidget(QLabel(t("Intervalo (minutos):")))
        self.notif_interval = QSpinBox()
        self.notif_interval.setRange(1, 480)
        self.notif_interval.setValue(30)
        self.notif_interval.setFixedWidth(80)
        self.notif_interval.valueChanged.connect(self._save_settings)
        interval_row.addWidget(self.notif_interval)
        interval_row.addStretch()
        notif_inner.addLayout(interval_row)

        msg_row = QVBoxLayout()
        msg_row.setSpacing(4)
        msg_row.addWidget(QLabel(t("Mensagem:")))
        self.notif_message = QLineEdit()
        self.notif_message.setPlaceholderText(t("Ex: Hora de fazer um check-in no Maestro!"))
        self.notif_message.setText(t("Hora de verificar suas tarefas no Maestro!"))
        self.notif_message.textChanged.connect(self._save_settings)
        msg_row.addWidget(self.notif_message)
        notif_inner.addLayout(msg_row)

        self.notif_settings_frame.setVisible(False)
        layout.addWidget(self.notif_settings_frame)

    def _on_notif_toggled(self, checked):
        self.notif_settings_frame.setVisible(checked)
        self._save_settings()

    def _load_settings(self):
        self._loading = True
        cfg = load_config()
        settings = cfg.get("settings", {})

        from maestro_local.config import get_language
        li = self.lang_combo.findData(get_language())
        if li >= 0:
            self.lang_combo.setCurrentIndex(li)

        self.pomodoro_duration.setValue(settings.get("pomodoro_minutes", 25))

        from maestro_local import eyecare
        eye = eyecare.config()
        self.eye_intervalo.setValue(eye["intervalo_min"])
        self.eye_duracao.setValue(eye["duracao_seg"])
        self.eye_adiar.setValue(eye["adiar_min"])

        from maestro_local.config import get_daily_focus_config
        foco = get_daily_focus_config()
        self.focus_enabled.setChecked(foco["enabled"])
        self.focus_message.setText(foco["message"])

        coach = settings.get("coach", {})
        self.coach_enabled.setChecked(coach.get("enabled", True))
        self.coach_interval.setValue(int(coach.get("interval_min", 90)))

        notif = settings.get("notifications", {})
        self.notif_enabled.setChecked(notif.get("enabled", False))
        self.notif_interval.setValue(notif.get("interval_minutes", 30))
        msg = notif.get("message", t("Hora de verificar suas tarefas no Maestro!"))
        self.notif_message.setText(msg)
        self.notif_settings_frame.setVisible(self.notif_enabled.isChecked())

        cron = settings.get("transcricoes", {})
        from maestro_local.transcricoes.constants import WHISPER_DEFAULT_LANGUAGE, WHISPER_DEFAULT_MODEL
        wm = cron.get("whisper_model", WHISPER_DEFAULT_MODEL)
        idx = self.whisper_model.findText(wm)
        if idx >= 0:
            self.whisper_model.setCurrentIndex(idx)
        self.whisper_lang.setText(cron.get("whisper_language", WHISPER_DEFAULT_LANGUAGE))
        self._loading = False

        self._load_ai_section()

    def _save_settings(self):
        if self._loading:
            return
        cfg = load_config()
        # `settings` é reescrito inteiro, então o que não estiver aqui some.
        # `last_shown` do foco do dia é gravado por outro caminho (ao exibir o
        # modal) e precisa sobreviver a um salvamento de configurações — senão
        # mexer em qualquer opção faria o modal reaparecer no mesmo dia.
        foco_anterior = cfg.get("settings", {}).get("daily_focus", {})
        cfg["settings"] = {
            "pomodoro_minutes": self.pomodoro_duration.value(),
            "daily_focus": {
                "enabled": self.focus_enabled.isChecked(),
                "message": self.focus_message.text().strip(),
                "last_shown": foco_anterior.get("last_shown", ""),
            },
            "coach": {
                "enabled": self.coach_enabled.isChecked(),
                "interval_min": self.coach_interval.value(),
            },
            "notifications": {
                "enabled": self.notif_enabled.isChecked(),
                "interval_minutes": self.notif_interval.value(),
                "message": self.notif_message.text(),
            },
            "transcricoes": {
                "whisper_model": self.whisper_model.currentText(),
                "whisper_language": self.whisper_lang.text().strip(),
            },
        }
        save_config(cfg)
        self.notification_changed.emit()

    def get_notification_settings(self):
        return {
            "enabled": self.notif_enabled.isChecked(),
            "interval_minutes": self.notif_interval.value(),
            "message": self.notif_message.text(),
        }

    def refresh(self):
        self._load_settings()
