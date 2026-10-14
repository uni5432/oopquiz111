import asyncio
import random
import time
from pathlib import Path

import flet as ft

from models import QuizBank, QuizGame, SessionLog
from widgets import (WIDTH, AnswerPanel, AppTitle, CountDropdown, LeaderboardTable, LoginField,
                     QuestionCard, ScoreText, StartButton, StatusText, TimerBar, column, row)


class QuizApp:
    TIME_LIMIT = 15.0
    TICK = 0.25
    PAUSE = 1.2
    REPORT_PATH = Path(__file__).with_name("report.txt")

    def __init__(self, page):
        self._page = page
        self._sessions = SessionLog()
        self._player = self._game = None
        self._token = 0
        self._answered = False
        page.title = "Столицы Европы"
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.scroll = ft.ScrollMode.AUTO
        page.window.width, page.window.height = 666, 666
        page.window.resizable = False
        page.window.prevent_close = True
        page.window.on_event = self._on_window_event
        self._build()

    def _build(self):
        self._login_field = LoginField(on_submit=self._on_start)
        self._count = CountDropdown()
        login_view = column(self._login_field, self._count,
                            StartButton(content="Начать игру", on_click=self._on_start))
        self._player_text = ft.Text(size=16)
        self._score_text = ScoreText()
        self._timer = TimerBar()
        self._card = QuestionCard()
        self._answers = AnswerPanel()
        self._status = StatusText()
        header = row(self._player_text, self._score_text, align=ft.MainAxisAlignment.SPACE_BETWEEN, width=WIDTH)
        quiz_view = column(header, self._timer, self._card, self._answers, self._status, visible=False)
        self._result = ft.Text(size=18, text_align=ft.TextAlign.CENTER)
        buttons = row(StartButton(content="Сыграть ещё", width=275, on_click=self._begin_game),
                      StartButton(content="Сменить игрока", width=275, on_click=self._on_switch))
        result_view = column(self._result, buttons, visible=False)
        self._views = (login_view, quiz_view, result_view)
        self._board = LeaderboardTable(columns=LeaderboardTable.make_columns())
        self._board.fill(self._sessions.roster())
        self._page.add(column(AppTitle(value="Квиз"), *self._views, ft.Divider(),
                              ft.Text("Игроки и их очки", size=20, weight=ft.FontWeight.BOLD), self._board,
                              spacing=16, width=WIDTH + 40))

    def _show(self, index):
        for i, view in enumerate(self._views):
            view.visible = i == index

    def _on_start(self, e):
        login = (self._login_field.value or "").strip()
        if login:
            self._player = self._sessions.open_session(login)
            self._begin_game()

    def _on_switch(self, e):
        self._sessions.close_session(self._player.login)
        self._login_field.value = ""
        self._show(0)
        self._page.update()

    def _begin_game(self, e=None):
        bank = QuizBank.build_questions()
        random.shuffle(bank)
        self._game = QuizGame(self._player, bank[:int(self._count.value)])
        self._player_text.value = f"Игрок: {self._player.login}"
        self._score_text.display(0)
        self._show(1)
        self._ask()

    def _ask(self):
        self._token += 1
        self._answered = False
        self._card.display(self._game.current, self._game.index + 1, len(self._game.questions))
        self._answers.build_for(self._game.current, self._on_answer)
        self._timer.fraction(1.0)
        self._status.value = ""
        self._page.update()
        self._page.run_task(self._countdown, self._token)

    async def _countdown(self, token):
        started = time.monotonic()
        while token == self._token:
            remaining = self.TIME_LIMIT - (time.monotonic() - started)
            if remaining <= 0:
                self._on_answer(None)
                return
            self._timer.fraction(remaining / self.TIME_LIMIT)
            self._page.update()
            await asyncio.sleep(self.TICK)

    def _on_answer(self, value):
        if self._answered:
            return
        self._answered, self._token = True, self._token + 1
        question = self._game.current
        correct = self._game.answer(value)
        self._answers.reveal(question, value)
        self._score_text.display(self._game.score)
        prefix = "Время вышло" if value is None else "Неверно"
        self._status.display(f"Верно +{question.points}" if correct
                             else f"{prefix}. Ответ: {question.correct_label()}", ok=correct)
        self._page.update()
        self._page.run_task(self._advance, self._token)

    async def _advance(self, token):
        await asyncio.sleep(self.PAUSE)
        if token != self._token:
            return
        self._game.index += 1
        if self._game.index >= len(self._game.questions):
            self._finish()
        else:
            self._ask()

    def _finish(self):
        game, player = self._game, self._player
        player.score = max(player.score, game.score)
        self._result.value = (f"Игра окончена, {player.login}!\n"
                              f"Правильных ответов: {game.correct_count} из {len(game.questions)}\n"
                              f"Очки за игру: {game.score}\nЛучший результат: {player.score}")
        self._board.fill(self._sessions.roster(), highlight=player.login)
        self._show(2)
        self._page.update()

    async def _on_window_event(self, e):
        if e.type == ft.WindowEventType.CLOSE:
            self._token += 1
            self._sessions.close_all()
            self.REPORT_PATH.write_text(self._sessions.report_text(), encoding="utf-8")
            await self._page.window.destroy()


if __name__ == "__main__":
    ft.run(QuizApp)
