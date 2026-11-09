"""Seed marked learning examples into an explicitly isolated Django database.

Required environment: DJANGO_SETTINGS_MODULE, LAT_DEMO_PASSWORD (8+ characters).
Optional environment: LAT_DEMO_EMAIL (default demo@lat-ai.local).
Run: python seed_learning.py --isolated-database

This file does not load .env files, change backend source, delete records, create
administrators, or store a plaintext password. It uses the configured Django ORM.
"""

import argparse
import json
import os
from datetime import timedelta


CATALOG = [
    {
        "key": "algebra",
        "title": "Алгебра: от дробей к уравнениям",
        "subject": "Математика",
        "description": "Научись работать с долями, находить проценты и решать линейные уравнения. В каждом уроке — объяснение, разобранный пример и одно самостоятельное задание.",
        "lessons": [
            {
                "key": "fractions",
                "title": "Доли и дроби",
                "content": "Что означает дробь\n\nДробь описывает часть целого. В записи 3/4 число 4 показывает, на сколько равных частей разделили целое, а число 3 — сколько таких частей взяли. Число сверху называют числителем, снизу — знаменателем.\n\nКак складывать дроби\n\nЕсли знаменатели одинаковы, сложи числители: 1/8 + 3/8 = 4/8. Знаменатель не меняется, потому что размер каждой части остаётся прежним. Дробь 4/8 можно сократить, разделив числитель и знаменатель на 4: получится 1/2.\n\nЕсли знаменатели различаются, сначала найди одинаковый размер частей. Например, 1/2 + 1/4 = 2/4 + 1/4 = 3/4.\n\nПример\n\nПирог разделён на 6 равных кусочков. Два съели утром и один вечером. Всего съели 2/6 + 1/6 = 3/6 = 1/2 пирога. Осталась другая половина.\n\nПроверь себя\n\nСумма съеденной и оставшейся долей должна равняться 1. Если получилось больше одного пирога, проверь вычисление и условие.",
                "exercise_title": "Сколько пиццы осталось?",
                "exercise": "Пиццу разделили на 8 одинаковых кусочков. Дана съела 2 кусочка, а друзья — ещё 3. Какая доля пиццы съедена? Какая осталась? Запиши вычисления и проверь, что две доли в сумме дают целую пиццу.",
                "attempt": {"status": "checked", "score": 92, "days_ago": 6, "answer": "Съедено (2 + 3)/8 = 5/8. Осталось 8/8 − 5/8 = 3/8. Проверка: 5/8 + 3/8 = 8/8 = 1.", "feedback": "Демонстрационный отзыв: доли и проверка записаны верно. Хорошо, что размер кусочков не меняется при сложении."},
            },
            {
                "key": "percentages",
                "title": "Проценты и скидки",
                "content": "Процент — одна сотая\n\n1% означает 1/100 целого. Поэтому 25% = 25/100 = 1/4, а 50% = 1/2. Чтобы найти процент от числа, переведи процент в десятичную дробь и умножь.\n\nПример со скидкой\n\nТетрадь стоит 800 условных единиц, скидка — 15%. Размер скидки: 800 × 0,15 = 120. Новая цена: 800 − 120 = 680. Можно сразу посчитать оставшиеся 85%: 800 × 0,85 = 680.\n\nКак узнать долю в процентах\n\nИз 20 заданий решены 16. Делим часть на целое и умножаем на 100%: 16 / 20 × 100% = 80%.\n\nЧастая ошибка\n\nВсегда уточняй, какое число принимается за 100%. Если цена 100 выросла на 10%, она стала 110. Снижение новой цены на 10% даст 99, а не 100, потому что второй процент считается от другого числа.\n\nПроверка\n\nСкидка 15% меньше четверти цены. Если рассчитанная скидка больше половины, вычисление неверно.",
                "exercise_title": "Новая цена книги",
                "exercise": "Книга стоит 1200 условных единиц. Скидка составляет 15%. Найди сумму скидки и цену после скидки. Затем проверь новую цену вторым способом — через оставшийся процент.",
                "attempt": {"status": "checked", "score": 88, "days_ago": 5, "answer": "Скидка: 1200 × 0,15 = 180. Цена: 1200 − 180 = 1020. Осталось 85%, поэтому 1200 × 0,85 тоже равно 1020.", "feedback": "Демонстрационный отзыв: оба способа дают правильный результат. В итоговом ответе добавь единицы цены."},
            },
            {
                "key": "equations",
                "title": "Линейные уравнения",
                "content": "Уравнение как равновесие\n\nУравнение — равенство с неизвестным числом. Например, x + 7 = 19. Нужно найти такое x, при котором левая и правая части равны.\n\nОсновное правило\n\nМожно выполнить одно и то же действие с обеими частями: прибавить или вычесть число, умножить или разделить на ненулевое число. Равенство сохранится.\n\nРазобранный пример\n\nРешим 3x + 6 = 24. Вычтем 6 из обеих частей: 3x = 18. Разделим обе части на 3: x = 6. Проверим подстановкой: 3 × 6 + 6 = 24.\n\nКак записывать решение\n\nКаждое преобразование записывай с новой строки. Сначала удобно убрать свободное слагаемое, затем коэффициент перед x. Не меняй знак без объяснения: это короткая запись действия с обеими частями.\n\nПроверка нужна всегда\n\nПодставь найденное число в исходное, а не в промежуточное уравнение. Это помогает заметить ошибку на любом шаге.",
                "exercise_title": "Найди неизвестное",
                "exercise": "Реши уравнение 4x + 6 = 30. Запиши действия с обеими частями и проверь найденное значение в исходном уравнении.",
                "attempt": {"status": "submitted", "days_ago": 0, "answer": "4x + 6 = 30. Вычитаю 6: 4x = 24. Делю на 4: x = 6. Проверка: 4 × 6 + 6 = 30."},
            },
        ],
    },
    {
        "key": "physics",
        "title": "Физика вокруг нас",
        "subject": "Физика",
        "description": "Пойми связь пути, времени и скорости, научись складывать силы и замечать превращения энергии в обычных ситуациях.",
        "lessons": [
            {
                "key": "speed",
                "title": "Путь, время и скорость",
                "content": "Что показывает скорость\n\nСредняя скорость — отношение всего пройденного пути ко всему времени движения: v = s / t. Если велосипедист проехал 12 км за 2 часа, средняя скорость равна 6 км/ч. Остановки включаются в общее время поездки.\n\nТри связанные формулы\n\nv = s / t; s = v × t; t = s / v. Сначала выпиши известные величины и то, что нужно найти.\n\nНе забывай единицы\n\nЕсли путь задан в километрах, а скорость нужна в км/ч, время должно быть в часах. 30 минут = 0,5 часа, 45 минут = 0,75 часа.\n\nРазобранный пример\n\nСамокат проехал 6 км за 30 минут. Переводим время: 30 / 60 = 0,5 часа. Скорость: 6 / 0,5 = 12 км/ч.\n\nПроверка\n\nЗа полчаса при скорости 12 км/ч получится половина 12 км, то есть 6 км. Результат совпадает с условием.",
                "exercise_title": "Прогулка до парка",
                "exercise": "Пешеход прошёл 3 км за 40 минут. Найди среднюю скорость в км/ч. Покажи перевод времени в часы и вычисление.",
                "attempt": {"status": "checked", "score": 94, "days_ago": 4, "answer": "40 минут = 40/60 часа = 2/3 часа. v = 3 / (2/3) = 4,5 км/ч. За 2/3 часа при такой скорости получится 3 км.", "feedback": "Демонстрационный отзыв: единицы согласованы, формула и проверка использованы правильно."},
            },
            {
                "key": "forces",
                "title": "Силы и равновесие",
                "content": "Сила — взаимодействие\n\nСила может изменить скорость тела или его форму. У силы есть величина и направление. Единица измерения — ньютон, обозначение Н.\n\nОдинаковые и противоположные направления\n\nЕсли две силы направлены вправо и равны 10 Н и 15 Н, их равнодействующая равна 25 Н вправо. Если 15 Н направлены вправо, а 10 Н влево, результат — 5 Н вправо.\n\nПример равновесия\n\nКнига лежит на столе. Сила тяжести действует вниз, а реакция опоры — вверх. Когда эти силы уравновешены, вертикальное движение не меняется.\n\nСила трения\n\nТрение обычно препятствует скольжению поверхностей друг относительно друга. В простой учебной задаче иногда предлагают не учитывать трение, чтобы рассмотреть только две заданные силы.\n\nКак решать\n\nНарисуй стрелки, выбери положительное направление, сложи силы с учётом знаков. В ответе укажи и величину, и направление.",
                "exercise_title": "Две силы действуют на ящик",
                "exercise": "Ящик тянут с силой 40 Н вправо и одновременно с силой 25 Н влево. Трение в этой задаче не учитывается. Найди величину и направление равнодействующей. Объясни, почему силы нужно вычитать.",
                "attempt": {"status": "submitted", "days_ago": 1, "answer": "Силы противоположны, поэтому вычитаю: 40 − 25 = 15 Н. Равнодействующая направлена вправо, в сторону большей силы."},
            },
            {
                "key": "energy",
                "title": "Как превращается энергия",
                "content": "Разные формы энергии\n\nДвижущееся тело обладает кинетической энергией. Поднятое над землёй тело обладает потенциальной энергией взаимодействия с Землёй. Ещё можно говорить об электрической и внутренней энергии.\n\nПадающий мяч\n\nПри падении мяча потенциальная энергия уменьшается, а кинетическая увеличивается. При ударе часть энергии переходит во внутреннюю энергию мяча и пола, часть — в звук. Поэтому мяч обычно не подскакивает на исходную высоту.\n\nЭнергия не исчезает\n\nВ замкнутой системе полная энергия сохраняется. Когда кажется, что движение исчезло из-за трения, энергия перешла в другие формы: например, поверхности нагрелись.\n\nПример с лампой\n\nЛампа получает электрическую энергию и передаёт её окружающей среде в виде света и тепла. Для освещения полезен свет, но тепло тоже нужно учитывать в общем энергетическом балансе.\n\nКак объяснять превращения\n\nНазови источник энергии, затем опиши действие и результат. Не используй выражение «энергия исчезла»: уточни, куда она передалась.",
                "exercise_title": "Почему нагреваются тормоза?",
                "exercise": "Велосипедист разогнался, а затем затормозил. Опиши, какие превращения энергии происходили при разгоне и торможении. Почему детали тормоза могут нагреться?",
            },
        ],
    },
    {
        "key": "english",
        "title": "Английский для общения",
        "subject": "Английский язык",
        "description": "Представься, расскажи о привычках и напиши короткое понятное сообщение. Уровень вводных уроков — A1–A2.",
        "lessons": [
            {
                "key": "introductions",
                "title": "Как рассказать о себе",
                "content": "Знакомство\n\nДля начала разговора хватит нескольких простых предложений: My name is Dana. I am fourteen. I live in Almaty. I like reading.\n\nГлагол be\n\nФормы зависят от того, о ком говорим: I am; you are; he, she, it is; we, they are. В разговорной речи часто используют сокращения: I’m, you’re, she’s.\n\nВопрос и ответ\n\nЧтобы задать вопрос с be, поставь глагол перед подлежащим: Are you a student? — Yes, I am. Для отрицания добавь not: I am not tired.\n\nНебольшой образец\n\nHi! My name is Sam. I am thirteen. I live in a small town. I like music and drawing. Nice to meet you!\n\nПроверь письмо\n\nМестоимение I, имена и названия городов пишут с заглавной буквы. В учебном ответе используй вымышленного персонажа: адрес и другие личные данные не нужны.",
                "exercise_title": "Знакомство с персонажем",
                "exercise": "Напиши четыре предложения о вымышленной ученице или ученике: имя, возраст, город и увлечение. Используй My name is, I am, I live и I like.",
                "attempt": {"status": "checked", "score": 90, "days_ago": 3, "answer": "My name is Alice. I am fourteen. I live in London. I like drawing.", "feedback": "Демонстрационный отзыв: все четыре конструкции употреблены правильно. Можно добавить короткое приветствие, чтобы знакомство звучало естественнее."},
            },
            {
                "key": "habits",
                "title": "Привычки: Present Simple",
                "content": "Регулярные действия\n\nPresent Simple помогает говорить о привычках: I read every evening. We play football on Saturdays.\n\nОкончание -s\n\nПосле he, she или it к обычному глаголу обычно добавляют -s: She reads. He plays. У некоторых форм есть особенности: go → goes; study → studies.\n\nОтрицание\n\nИспользуй do not или does not: I don’t play tennis. She doesn’t play tennis. После doesn’t основной глагол идёт без -s, потому что нужная форма уже выражена вспомогательным глаголом.\n\nВопрос\n\nDo you read every day? Does he read every day? Вопросы тоже используют основную форму read.\n\nКак часто\n\nUsually, often и sometimes показывают частоту: I usually read at home. She often listens to music. В таких примерах слово частоты стоит перед основным глаголом.",
                "exercise_title": "Расскажи о привычках",
                "exercise": "Переведи: «Она обычно читает вечером» и «Он не играет в футбол». Затем задай на английском вопрос «Ты читаешь каждый день?». Объясни, почему после doesn’t не нужно окончание -s.",
            },
            {
                "key": "messages",
                "title": "Короткое сообщение другу",
                "content": "Три части сообщения\n\nПонятное сообщение содержит приветствие, цель и завершение. Например: Hi Sam! Can we study together on Friday? Let’s meet at the library at 4 pm. See you!\n\nДень, время и место\n\nПеред днём недели используют on: on Friday. Перед временем — at: at 4 pm. Для места в примере подходит at the library.\n\nВежливые просьбы\n\nCan you help me? — обычная вежливая просьба. Could you help me? звучит немного мягче. Для предложения можно использовать Let’s: Let’s study together.\n\nПроверка перед отправкой\n\nПонятно ли, что ты предлагаешь, где и когда? Если информации слишком много, раздели её на короткие предложения.\n\nСамостоятельный пример\n\nHi Mia! Let’s practise English on Saturday. Can we meet at the school library at 11 am? See you! Для учебных сообщений достаточно вымышленных имён и общественных мест.",
                "exercise_title": "Приглашение позаниматься",
                "exercise": "Напиши 3–4 предложения вымышленному другу: предложи вместе подготовиться к уроку, укажи день, время и общественное место. Добавь приветствие и завершение.",
            },
        ],
    },
    {
        "key": "python",
        "title": "Первые программы на Python",
        "subject": "Программирование",
        "description": "Разберись с переменными, условиями и циклами. Задания проверяют понимание кода и принимают текстовый ответ; браузер не запускает программы.",
        "lessons": [
            {
                "key": "variables",
                "title": "Переменные и значения",
                "content": "Имя для значения\n\nПеременная связывает имя со значением. Запись age = 14 означает, что имя age сейчас связано с числом 14. Строку записывают в кавычках: name = \"Dana\".\n\nНесколько типов\n\nint — целые числа; float — числа с дробной частью; str — текст; bool — логические значения True и False. Для чисел знак + означает сложение, для строк — соединение текста.\n\nПрисваивание\n\napples = 3\napples = apples + 2\nprint(apples)\n\nВо второй строке сначала вычисляется правая часть: 3 + 2. Затем результат 5 сохраняется под именем apples. Последняя строка выводит 5.\n\nЗначение не меняется само\n\nprint(apples + 1) выведет 6, но apples останется равным 5. Чтобы изменить переменную, нужно новое присваивание.\n\nКак разбирать код\n\nЧитай строки сверху вниз и рядом записывай текущее значение каждой переменной. В этих уроках код нужно объяснить текстом: его выполнение в браузере не предусмотрено.",
                "exercise_title": "Что выведет программа?",
                "exercise": "Разбери код: points = 7; points = points + 3; print(points * 2). Что будет выведено? Чему после этого равно points? Объясни разницу между выводом выражения и присваиванием.",
            },
            {
                "key": "conditions",
                "title": "Условия if и else",
                "content": "Программа выбирает действие\n\nУсловие if проверяет выражение, результат которого — True или False. Если условие верно, выполняется первый блок. Иначе может выполниться блок else.\n\nПример\n\nif temperature < 10:\n    print(\"Надень куртку\")\nelse:\n    print(\"Можно идти без куртки\")\n\nВ Python отступы показывают, какие строки относятся к каждому блоку.\n\nЗнаки сравнения\n\n== означает равно, != — не равно, < и > — меньше и больше, <= и >= — меньше или равно и больше или равно. Один знак = выполняет присваивание, а не сравнение.\n\nГраница условия\n\nВ условии score >= 60 число 60 подходит, потому что знак включает равенство. В score > 60 это же число уже не подходит.\n\nКак проверить\n\nПодставь число меньше границы, равное границе и больше границы. Три таких примера помогают заметить ошибку в сравнении.",
                "exercise_title": "Проверка результата",
                "exercise": "Напиши или опиши условие: если score не меньше 60, вывести «Зачёт», иначе «Попробуй ещё». Укажи результат при score = 59, 60 и 61.",
            },
            {
                "key": "loops",
                "title": "Циклы без повторения строк",
                "content": "Зачем нужен цикл\n\nЦикл for повторяет действия для каждого элемента последовательности. Вместо четырёх похожих строк можно написать один блок и указать список значений.\n\nПример суммы\n\ntotal = 0\nfor n in [1, 2, 3, 4]:\n    total = total + n\nprint(total)\n\nПосле каждого шага total меняется: 1, затем 3, затем 6, затем 10. Последняя строка расположена без отступа, поэтому выполнится один раз после цикла.\n\nПоследовательность range\n\nrange(3) даёт 0, 1, 2. Правая граница не включается. Поэтому цикл for i in range(3) выполняется три раза.\n\nЧастая ошибка\n\nЕсли total = 0 поместить внутрь цикла, сумма будет сбрасываться на каждом шаге. Начальное значение накопителя задают перед циклом.\n\nКак проверить\n\nСоставь небольшую таблицу: номер шага, текущее n, новое total. Затем сравни итог с обычной суммой.",
                "exercise_title": "Накопление суммы",
                "exercise": "Как изменится total, если перед циклом записано total = 0, а цикл перебирает [2, 4, 6] и выполняет total = total + n? Запиши значение после каждого шага и объясни, почему total = 0 должно стоять перед циклом.",
            },
        ],
    },
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-database", action="store_true", help="Confirm that DJANGO_SETTINGS_MODULE targets the isolated demonstration database.")
    args = parser.parse_args()
    if not args.isolated_database:
        parser.error("Run only against the isolated database, with --isolated-database.")
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        parser.error("Set DJANGO_SETTINGS_MODULE to the isolated runtime settings; no .env is loaded by this script.")
    password = os.environ.get("LAT_DEMO_PASSWORD", "")
    if len(password) < 8:
        parser.error("Set LAT_DEMO_PASSWORD to a value of at least 8 characters.")
    email = os.environ.get("LAT_DEMO_EMAIL", "demo@lat-ai.local").strip()

    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.validators import validate_email
    from django.db import transaction
    from django.utils import timezone
    from courses.models import Course, Lesson, Exercise
    from progress.models import LessonProgress, ExerciseAttempt

    validate_email(email)
    User = get_user_model()
    email = User.objects.normalize_email(email)
    if len(email) > 150:
        raise ValueError("Demo email must fit the username field (150 characters).")
    marker = "LAT-DEMO:v1"
    visible_marker = "Учебный пример LAT AI"
    counts = {"created": {}, "updated": {}}

    def count(action, model):
        name = model.__name__
        counts[action][name] = counts[action].get(name, 0) + 1

    def upsert_owned(model, lookup, values):
        rows = list(model.objects.filter(**lookup)[:2])
        if len(rows) > 1:
            raise RuntimeError("Ambiguous marked objects for " + model.__name__ + "; nothing will be committed.")
        if not rows:
            obj = model.objects.create(**values)
            count("created", model)
            return obj, True
        obj = rows[0]
        changed = []
        for name, value in values.items():
            if getattr(obj, name) != value:
                setattr(obj, name, value)
                changed.append(name)
        if changed:
            if hasattr(obj, "updated_at"):
                changed.append("updated_at")
            obj.save(update_fields=changed)
            count("updated", model)
        return obj, False

    with transaction.atomic():
        user = User.objects.filter(email=email).first()
        if user and (user.first_name != marker or user.role != "student" or user.is_staff or user.is_superuser):
            raise RuntimeError("Email is already used by an unmarked or privileged account. Choose a separate LAT_DEMO_EMAIL; no records changed.")
        if not user:
            if User.objects.filter(username=email).exists():
                raise RuntimeError("Username collision with an existing account; no records changed.")
            user = User.objects.create_user(email=email, password=password, display_name="Дана", first_name=marker, role="student", is_staff=False, is_superuser=False, is_active=True)
            count("created", User)
        else:
            changed = []
            if user.display_name != "Дана":
                user.display_name = "Дана"
                changed.append("display_name")
            if not user.is_active:
                user.is_active = True
                changed.append("is_active")
            if not user.check_password(password):
                user.set_password(password)
                changed.append("password")
            if changed:
                user.save(update_fields=changed)
                count("updated", User)

        seeded_lessons = []
        seeded_courses = []
        for course_index, spec in enumerate(CATALOG):
            course_marker = visible_marker + " · " + spec["title"] + "."
            course, _ = upsert_owned(Course, {"description__contains": course_marker}, {
                "title": spec["title"], "subject": spec["subject"], "is_published": True,
                "description": spec["description"] + "\n\n" + course_marker,
            })
            seeded_courses.append(course)
            for index, item in enumerate(spec["lessons"], 1):
                item_marker = visible_marker + " · " + spec["title"] + " · " + item["title"] + "."
                lesson, _ = upsert_owned(Lesson, {"course": course, "content__contains": item_marker}, {
                    "course": course, "title": item["title"], "order": index,
                    "content": item["content"] + "\n\n" + item_marker,
                })
                seeded_lessons.append(lesson)
                exercise, _ = upsert_owned(Exercise, {"lesson": lesson, "description__contains": item_marker}, {
                    "lesson": lesson, "title": item["exercise_title"], "description": item["exercise"] + "\n\n" + item_marker,
                    "task_type": "text", "order": 1, "max_score": 100, "is_published": True,
                })
                sample = item.get("attempt")
                if sample:
                    answer = sample["answer"] + "\n\n" + item_marker
                    attempt, created = upsert_owned(ExerciseAttempt, {"user": user, "exercise": exercise, "answer__contains": item_marker}, {
                        "user": user, "exercise": exercise, "answer": answer,
                        "status": sample["status"], "score": sample.get("score"), "feedback": sample.get("feedback", ""),
                    })
                    if created:
                        # Backdate once; reruns never move these examples above new user answers.
                        when = user.date_joined - timedelta(days=sample["days_ago"], minutes=course_index + index)
                        ExerciseAttempt.objects.filter(pk=attempt.pk).update(submitted_at=when)

        # Match the supplied backend's rule: latest attempts for every published
        # exercise must be checked. Real later answers in this demo account remain intact.
        for lesson in seeded_lessons:
            exercises = list(Exercise.objects.filter(lesson=lesson, is_published=True))
            total_score = 0
            all_checked = bool(exercises)
            for exercise in exercises:
                latest = ExerciseAttempt.objects.filter(user=user, exercise=exercise).order_by("-submitted_at", "-id").first()
                if not latest or latest.status != "checked":
                    all_checked = False
                    break
                if exercise.max_score > 0:
                    total_score += (latest.score or 0) / exercise.max_score * 100
            score = total_score / len(exercises) if all_checked else None
            upsert_owned(LessonProgress, {"user": user, "lesson": lesson}, {
                "user": user, "lesson": lesson, "completed": all_checked, "score": score,
            })

        result = {
            "status": "ok", "user": {"id": user.pk, "email": user.email, "display_name": user.display_name, "role": user.role},
            "marked_courses": len(seeded_courses), "marked_lessons": len(seeded_lessons),
            "course_ids": [course.pk for course in seeded_courses],
            "completed_lessons": LessonProgress.objects.filter(user=user, lesson__in=seeded_lessons, completed=True).count(),
            "marked_attempts": ExerciseAttempt.objects.filter(user=user, exercise__lesson__in=seeded_lessons, answer__contains=visible_marker + " · ").count(),
            "changes": counts,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
