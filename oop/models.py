from abc import ABC, abstractmethod
from datetime import datetime
from functools import total_ordering

TIME_FORMAT = "%d.%m.%Y %H:%M:%S"


def field(name, check=None):
    def getter(self):
        return getattr(self, "_" + name)

    def setter(self, value):
        setattr(self, "_" + name, check(value) if check else value)

    return property(getter, setter)


def integer(minimum):
    def check(value):
        if type(value) is not int or value < minimum:
            raise ValueError(f"Нужно целое число не меньше {minimum}")
        return value

    return check


def non_empty(value):
    if not str(value).strip():
        raise ValueError("значение не может быть пустым")
    return str(value).strip()


@total_ordering
class Entity(ABC):
    _counter = 0
    id = field("id", integer(1))

    def __init__(self):
        Entity._counter += 1
        self.id = Entity._counter

    @abstractmethod
    def describe(self) -> str: ...

    @abstractmethod
    def ident(self) -> tuple: ...

    def rank(self) -> tuple:
        return ()

    def __eq__(self, other):
        return type(self) is type(other) and self.ident() == other.ident()

    def __lt__(self, other):
        if not isinstance(other, Entity):
            return NotImplemented
        return (self.rank(), self.ident()) < (other.rank(), other.ident())

    def __hash__(self):
        return hash(self.ident())

    def __repr__(self):
        return f"{type(self).__name__}({self.describe()})"

    def __str__(self):
        return self.describe()


class PairMap:
    def __init__(self):
        self._pairs = []

    def __setitem__(self, key, value):
        for pair in self._pairs:
            if pair[0] == key:
                pair[1] = value
                return
        self._pairs.append([key, value])

    def __getitem__(self, key):
        for pair in self._pairs:
            if pair[0] == key:
                return pair[1]
        raise KeyError(key)

    def __contains__(self, key):
        return any(pair[0] == key for pair in self._pairs)

    def __len__(self):
        return len(self._pairs)

    def values(self):
        return [pair[1] for pair in self._pairs]


class Question(Entity):
    kind = ""
    text = field("text", non_empty)
    points = field("points", integer(1))

    def __init__(self, text, points):
        super().__init__()
        self.text = text
        self.points = points

    def ident(self):
        return (self._text,)

    def rank(self):
        return (self._points,)

    def describe(self):
        return f"[{self.kind}] {self._text} ({self._points})"

    def check(self, answer) -> bool:
        return answer == self.correct_key() and type(answer) is type(self.correct_key())

    @abstractmethod
    def correct_key(self): ...

    @abstractmethod
    def correct_label(self) -> str: ...


class ChoiceQuestion(Question):
    kind = "choice"
    options = field("options", tuple)
    correct_index = field("correct_index", integer(0))

    def __init__(self, text, options, correct_index, points=10):
        super().__init__(text, points)
        self.options = options
        self.correct_index = correct_index

    def correct_key(self):
        return self._correct_index

    def correct_label(self):
        return self._options[self._correct_index]


class TrueFalseQuestion(Question):
    kind = "bool"
    correct = field("correct", bool)

    def __init__(self, text, correct, points=5):
        super().__init__(text, points)
        self.correct = correct

    def correct_key(self):
        return self._correct

    def correct_label(self):
        return "Верно" if self._correct else "Неверно"


class Player(Entity):
    login = field("login", non_empty)
    score = field("score", integer(0))

    def __init__(self, login, score=0):
        super().__init__()
        self.login = login
        self.score = score

    def ident(self):
        return (self._login,)

    def rank(self):
        return (self._score,)

    def describe(self):
        return f"{self._login}: {self._score}"


class Session(Entity):
    player = field("player")
    time_in = field("time_in")
    time_out = field("time_out")

    def __init__(self, player, time_in, time_out=None):
        super().__init__()
        self.player, self.time_in, self.time_out = player, time_in, time_out

    @property
    def is_active(self):
        return self._time_out is None

    def close(self):
        self.time_out = datetime.now()

    @staticmethod
    def format_time(moment) -> str:
        return "" if moment is None else moment.strftime(TIME_FORMAT)

    def ident(self):
        return (self._player.login, self._time_in)

    def rank(self):
        return (self._time_in,)

    def describe(self):
        return f"{self._player.login}: {self.format_time(self._time_in)} - {self.format_time(self._time_out)}"


class QuizGame(Entity):
    player = field("player")
    questions = field("questions")
    score = field("score", integer(0))
    index = field("index", integer(0))
    correct_count = field("correct_count", integer(0))

    def __init__(self, player, questions):
        super().__init__()
        self.player = player
        self.questions = list(questions)
        self.index = self.score = self.correct_count = 0

    @property
    def current(self):
        return self.questions[self._index]

    def answer(self, value):
        correct = value is not None and self.current.check(value)
        if correct:
            self._score += self.current.points
            self._correct_count += 1
        return correct

    def ident(self):
        return (self.id,)

    def describe(self):
        return f"{self._player.login}: {self._score} очков, вопрос {self._index}/{len(self.questions)}"


class QuizBank:
    @staticmethod
    def build_questions():
        return [
            ChoiceQuestion("Столица Исландии?", ("Рейкьявик", "Осло", "Хельсинки", "Копенгаген"), 0),
            ChoiceQuestion("Столица Португалии?", ("Порту", "Лиссабон", "Мадрид", "Фару"), 1),
            ChoiceQuestion("Столица Ирландии?", ("Корк", "Белфаст", "Дублин", "Голуэй"), 2),
            ChoiceQuestion("Столица Испании?", ("Барселона", "Мадрид", "Севилья", "Валенсия"), 1),
            ChoiceQuestion("Столица Великобритании?", ("Манчестер", "Эдинбург", "Ливерпуль", "Лондон"), 3),
            ChoiceQuestion("Столица Франции?", ("Париж", "Лион", "Марсель", "Ницца"), 0),
            ChoiceQuestion("Столица Бельгии?", ("Антверпен", "Гент", "Брюссель", "Брюгге"), 2),
            TrueFalseQuestion("Роттердам — столица Нидерландов.", False),
            ChoiceQuestion("Столица Швейцарии?", ("Цюрих", "Женева", "Берн", "Базель"), 2),
            ChoiceQuestion("Столица Норвегии?", ("Берген", "Осло", "Тронхейм", "Ставангер"), 1),
            TrueFalseQuestion("Милан — столица Италии.", False),
            ChoiceQuestion("Столица Дании?", ("Орхус", "Копенгаген", "Оденсе", "Ольборг"), 1),
            ChoiceQuestion("Столица Германии?", ("Мюнхен", "Гамбург", "Франкфурт", "Берлин"), 3),
            TrueFalseQuestion("Прага — столица Чехии.", True),
            ChoiceQuestion("Столица Австрии?", ("Зальцбург", "Грац", "Вена", "Инсбрук"), 2),
            ChoiceQuestion("Столица Швеции?", ("Гётеборг", "Стокгольм", "Мальмё", "Уппсала"), 1),
            ChoiceQuestion("Столица Польши?", ("Краков", "Гданьск", "Варшава", "Вроцлав"), 2),
            TrueFalseQuestion("Хельсинки — столица Финляндии.", True),
        ]

    @staticmethod
    def demo_players():
        names = ("monica", "erica", "rita", "tina", "sandra", "marry", "jessica", "liam", "noah", "james")
        scores = (85, 70, 60, 95, 40, 75, 55, 100, 30, 65)
        return [Player(name, score) for name, score in zip(names, scores)]


class ReportWriter:
    HEADERS = ("login", "time_in", "time_out")

    @staticmethod
    def format_table(rows) -> str:
        widths = [max([len(h)] + [len(r[i]) for r in rows]) for i, h in enumerate(ReportWriter.HEADERS)]
        border = "+" + "-" * (sum(w + 2 for w in widths) + len(widths) - 1) + "+"
        head = "| " + " | ".join(h.center(w) for h, w in zip(ReportWriter.HEADERS, widths)) + " |"
        sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        body = ["| " + " | ".join(c.ljust(w) for c, w in zip(row, widths)) + " |" for row in rows]
        return "\n".join([border, head, sep] + body + [border]) + "\n"


class SessionLog(Entity):
    def __init__(self):
        super().__init__()
        self._players = PairMap()
        self._sessions = []
        for player in QuizBank.demo_players():
            self._players[player.login] = player

    def roster(self):
        return self._players.values()

    def active_session(self, login):
        return next((s for s in self._sessions if s.player.login == login and s.is_active), None)

    def open_session(self, login):
        player = self._players[login] if login in self._players else Player(login)
        self._players[player.login] = player
        if self.active_session(login) is None:
            self._sessions.append(Session(player, datetime.now()))
        return player

    def close_session(self, login):
        session = self.active_session(login)
        if session is not None:
            session.close()

    def close_all(self):
        for session in self._sessions:
            if session.is_active:
                session.close()

    def report_text(self) -> str:
        return ReportWriter.format_table([(s.player.login, Session.format_time(s.time_in),
                                           Session.format_time(s.time_out)) for s in sorted(self._sessions)])

    def ident(self):
        return (self.id,)

    def describe(self):
        return f"SessionLog: {len(self._players)} игроков, {len(self._sessions)} сеансов"