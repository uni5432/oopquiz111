import flet as ft

WIDTH = 666


@ft.control
class AppTitle(ft.Text):
    def init(self):
        self.size, self.weight, self.text_align = 28, ft.FontWeight.BOLD, ft.TextAlign.CENTER


@ft.control
class LoginField(ft.TextField):
    def init(self):
        self.label, self.max_length, self.autofocus, self.width = "Логин", 20, True, WIDTH


@ft.control
class CountDropdown(ft.Dropdown):
    def init(self):
        self.label, self.value, self.width = "Число вопросов", "18", WIDTH
        self.options = [ft.DropdownOption(key=str(n), text=str(n)) for n in (6, 12, 18)]


@ft.control
class StartButton(ft.Button):
    def init(self):
        self.height, self.width = 48, self.width or WIDTH


@ft.control
class AnswerButton(ft.OutlinedButton):
    answer: object = None

    def init(self):
        self.height, self.width = 48, self.width or WIDTH

    def mark(self, state):
        self.style = ft.ButtonStyle(bgcolor=ft.Colors.GREEN_200 if state == "correct"
                                    else ft.Colors.RED_200 if state == "wrong" else None)


@ft.control
class TimerBar(ft.ProgressBar):
    def init(self):
        self.value, self.bar_height, self.width = 1.0, 10, WIDTH

    def fraction(self, value):
        self.value = max(0.0, min(1.0, value))
        self.color = ft.Colors.GREEN if value > 0.5 else ft.Colors.ORANGE if value > 0.25 else ft.Colors.RED


@ft.control
class ScoreText(ft.Text):
    def init(self):
        self.size, self.weight, self.value = 18, ft.FontWeight.BOLD, "Очки: 0"

    def display(self, score):
        self.value = f"Очки: {score}"


@ft.control
class StatusText(ft.Text):
    def init(self):
        self.size, self.height, self.weight = 16, 28, ft.FontWeight.BOLD
        self.text_align = ft.TextAlign.CENTER

    def display(self, message, ok=True):
        self.color = ft.Colors.GREEN_700 if ok else ft.Colors.RED_700
        self.value = message


@ft.control
class QuestionCard(ft.Card):
    def init(self):
        self._number = ft.Text(size=14, color=ft.Colors.GREY_700)
        self._text = ft.Text(size=20, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER)
        self.width = WIDTH
        self.content = ft.Container(padding=ft.Padding.all(16), content=ft.Column(
            controls=[self._number, self._text], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8))

    def display(self, question, position, total):
        self._number.value = f"Вопрос {position} из {total}  ·  {question.points} очк."
        self._text.value = question.text


@ft.control
class LeaderboardTable(ft.DataTable):
    def init(self):
        self.width, self.column_spacing = WIDTH, 20

    @staticmethod
    def make_columns():
        return [ft.DataColumn(label=ft.Text("#")), ft.DataColumn(label=ft.Text("Игрок")),
                ft.DataColumn(label=ft.Text("Очки"), numeric=True)]

    def fill(self, players, highlight=None):
        self.rows = []
        for place, player in enumerate(players, start=1):
            bold = ft.FontWeight.BOLD if player.login == highlight else ft.FontWeight.NORMAL
            cells = (str(place), player.login, str(player.score))
            self.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(c, weight=bold)) for c in cells]))


@ft.control
class AnswerPanel(ft.Column):
    def init(self):
        self.spacing, self.horizontal_alignment = 10, ft.CrossAxisAlignment.CENTER
        self._buttons = []
        self._locked = False

    def build_for(self, question, on_answer):
        self._locked, self._on_answer = False, on_answer
        is_choice = question.kind == "choice"
        labels = list(enumerate(question.options)) if is_choice else [(True, "Верно"), (False, "Неверно")]
        self._buttons = [AnswerButton(content=text, answer=key, width=WIDTH if is_choice else 275,
                                      on_click=self._click) for key, text in labels]
        self.controls = list(self._buttons) if is_choice else [
            ft.Row(controls=list(self._buttons), alignment=ft.MainAxisAlignment.CENTER, spacing=10)]

    def _click(self, e):
        if not self._locked:
            self._on_answer(e.control.answer)

    def reveal(self, question, chosen):
        self._locked = True
        for button in self._buttons:
            wrong = chosen is not None and button.answer == chosen and type(button.answer) is type(chosen)
            button.mark("correct" if question.check(button.answer) else "wrong" if wrong else "idle")


def column(*controls, visible=True, width=None, spacing=12):
    return ft.Column(controls=list(controls), horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                     spacing=spacing, visible=visible, width=width)


def row(*controls, align=ft.MainAxisAlignment.CENTER, width=None):
    return ft.Row(controls=list(controls), alignment=align, spacing=10, width=width)
