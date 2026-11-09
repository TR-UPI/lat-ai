"""Verify the real LAT AI Django API; adds three labelled study documents.

Credentials are read only from LAT_DEMO_EMAIL and LAT_DEMO_PASSWORD.
Optional LAT_API_BASE defaults to http://127.0.0.1:8000/api/v1.
No deletes, review actions, answer submissions, or backend changes are performed.
Only status/count summaries are printed; response bodies and credentials are not.
Uses Python's standard library only.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import uuid


MATERIALS_DIR = Path(__file__).resolve().parent / "demo-materials"
MATERIAL_TEXTS = {
  "lat-ai-algebra.txt": "Учебный пример LAT AI\nАлгебра: линейные и квадратные уравнения\n\nЛинейное уравнение с одной переменной имеет вид ax + b = 0. Если a не равно нулю, уравнение имеет единственное решение x = -b/a. Для решения можно переносить слагаемые из одной части в другую, меняя знак, и делить обе части на одно и то же ненулевое число. Проверка выполняется подстановкой найденного значения в исходное равенство.\n\nПример: 3x + 6 = 18. Вычтем 6 из обеих частей: 3x = 12. Разделим обе части на 3: x = 4. Проверка: 3 · 4 + 6 = 18. Ответ верный.\n\nКвадратное уравнение имеет вид ax² + bx + c = 0, где a не равно нулю. Дискриминант вычисляется по формуле D = b² - 4ac. Если D больше нуля, существуют два различных действительных корня. Если D равен нулю, есть один действительный корень кратности два. Если D меньше нуля, действительных корней нет. Формула корней: x₁,₂ = (-b ± √D)/(2a).\n\nПример: x² - 5x + 6 = 0. Здесь a = 1, b = -5, c = 6. Получаем D = 25 - 24 = 1. Корни: x₁ = (5 - 1)/2 = 2 и x₂ = (5 + 1)/2 = 3. Проверка: 2² - 5 · 2 + 6 = 0 и 3² - 5 · 3 + 6 = 0.\n\nВажно не терять знак коэффициента b и не забывать скобки при подстановке отрицательных чисел. Чтобы найти количество действительных корней квадратного уравнения, достаточно сначала вычислить дискриминант и сравнить его с нулём.\n\nМатериал создан как учебный пример для проверки загрузки документов и поиска по содержимому в LAT AI.\n",
  "lat-ai-geometry.txt": "Учебный пример LAT AI\nГеометрия: прямоугольный треугольник\n\nПрямоугольный треугольник имеет один угол 90 градусов. Две стороны, образующие прямой угол, называются катетами. Сторона напротив прямого угла называется гипотенузой. Гипотенуза всегда длиннее каждого катета.\n\nТеорема Пифагора связывает длины сторон прямоугольного треугольника: a² + b² = c², где a и b — катеты, а c — гипотенуза. Теорему нельзя применять к произвольному треугольнику без проверки наличия прямого угла.\n\nПример: катеты равны 6 см и 8 см. Тогда квадрат гипотенузы равен 6² + 8² = 36 + 64 = 100. Длина гипотенузы равна √100 = 10 см. Периметр такого треугольника составляет 6 + 8 + 10 = 24 см.\n\nПлощадь прямоугольного треугольника равна половине произведения его катетов: S = ab/2. Для катетов 6 см и 8 см получаем S = 6 · 8 / 2 = 24 см². Длина измеряется в сантиметрах, а площадь — в квадратных сантиметрах; единицы нельзя смешивать.\n\nЕсли известны гипотенуза c и катет a, второй катет можно найти по формуле b = √(c² - a²). Например, при c = 13 см и a = 5 см имеем b = √(169 - 25) = √144 = 12 см.\n\nЧтобы проверить, является ли треугольник прямоугольным, выбирают самую длинную сторону и сравнивают квадрат её длины с суммой квадратов двух других сторон. Равенство подтверждает прямой угол по обратной теореме Пифагора.\n\nМатериал создан как учебный пример для проверки загрузки документов и поиска по содержимому в LAT AI.\n",
  "lat-ai-physics.txt": "Учебный пример LAT AI\nФизика: скорость и равномерное движение\n\nРавномерным называют движение, при котором тело за любые равные промежутки времени проходит равные пути. Средняя скорость показывает отношение пройденного пути ко времени движения. Основная формула: v = s/t, где v — скорость, s — путь, t — время. При равномерном движении путь вычисляется как s = vt, а время — как t = s/v.\n\nВ Международной системе единиц путь измеряют в метрах, время — в секундах, скорость — в метрах в секунду. В транспортных задачах часто применяют километры в час. Для перевода скорости из км/ч в м/с нужно разделить числовое значение на 3,6. Для обратного перевода из м/с в км/ч нужно умножить на 3,6.\n\nПример: автомобиль едет со скоростью 72 км/ч. Переведём её в метры в секунду: 72 / 3,6 = 20 м/с. За 15 секунд при постоянной скорости автомобиль пройдёт s = 20 · 15 = 300 м.\n\nПример на время: велосипедист должен проехать 18 км со скоростью 12 км/ч. Время t = 18 / 12 = 1,5 часа, то есть 1 час 30 минут. Нельзя подставлять путь в километрах и скорость в метрах в секунду без предварительного приведения единиц.\n\nСредняя скорость за весь путь равна всему пройденному пути, делённому на всё затраченное время. Она не всегда равна среднему арифметическому скоростей отдельных участков. Например, за первый час пройдено 10 км, а за следующие два часа — 20 км. Средняя скорость за три часа равна 30 / 3 = 10 км/ч.\n\nМатериал создан как учебный пример для проверки загрузки документов и поиска по содержимому в LAT AI.\n"
}
SEARCHES = {
    "lat-ai-algebra.txt": "Как по дискриминанту определить количество действительных корней квадратного уравнения?",
    "lat-ai-geometry.txt": "Как найти гипотенузу и площадь прямоугольного треугольника по двум катетам?",
    "lat-ai-physics.txt": "Как перевести скорость из километров в час в метры в секунду?",
}


class CheckFailure(Exception):
    def __init__(self, stage, code, http_status=None):
        self.stage = stage
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def emit(stage, status="ok", **counts):
    print(json.dumps({"check": stage, "status": status, **counts},
                     ensure_ascii=True), flush=True)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class API:
    def __init__(self, base):
        parsed = urlsplit(base.strip())
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.username or parsed.password or parsed.query
                or parsed.fragment):
            raise CheckFailure("configuration", "invalid_base_url")
        self.base = base.strip().rstrip("/") + "/"
        self.origin = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        self.opener = build_opener(NoRedirects())
        self.token = None

    def url(self, endpoint):
        target = urljoin(self.base, endpoint)
        if not target.startswith(self.base):
            raise CheckFailure("pagination", "url_outside_api")
        return target

    def call(self, stage, endpoint, method="GET", payload=None,
             file_path=None, timeout=60, health=False):
        target = self.origin + "/health/" if health else self.url(endpoint)
        headers = {"Accept": "application/json"}
        if self.token and not health:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        if file_path is not None:
            boundary = "lat-ai-" + uuid.uuid4().hex
            prefix = (
                "--" + boundary + "\r\n"
                'Content-Disposition: form-data; name="file"; filename="'
                + file_path.name + '"\r\n'
                "Content-Type: text/plain; charset=utf-8\r\n\r\n"
            ).encode("utf-8")
            body = prefix + file_path.read_bytes() + (
                "\r\n--" + boundary + "--\r\n"
            ).encode("ascii")
            headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        elif payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(target, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=timeout) as response:
                raw = response.read()
                data = json.loads(raw.decode("utf-8")) if raw else None
                return data
        except HTTPError as error:
            # Never print error bodies, which may contain private Django details.
            raise CheckFailure(stage, "http_error", error.code) from None
        except (URLError, TimeoutError, socket.timeout):
            raise CheckFailure(stage, "connection_or_timeout") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise CheckFailure(stage, "invalid_json") from None

    def collection(self, stage, endpoint):
        result = []
        seen = set()
        next_url = endpoint
        while next_url:
            target = self.url(next_url)
            if target in seen or len(seen) >= 100:
                raise CheckFailure(stage, "invalid_pagination")
            seen.add(target)
            data = self.call(stage, target)
            if isinstance(data, list):
                return result + data
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise CheckFailure(stage, "invalid_list_shape")
            result.extend(data["results"])
            next_url = data.get("next")
        return result


def object_id(value, stage):
    if not isinstance(value, dict):
        raise CheckFailure(stage, "invalid_object_shape")
    value = value.get("id")
    if type(value) is not int or value < 1:
        raise CheckFailure(stage, "invalid_object_id")
    return value


def prepare_materials():
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for filename, content in MATERIAL_TEXTS.items():
        target = MATERIALS_DIR / filename
        if not target.exists():
            target.write_text(content, encoding="utf-8")
        actual = target.read_text(encoding="utf-8-sig")
        if not actual.startswith("Учебный пример LAT AI"):
            raise CheckFailure("materials", "missing_study_example_label")
        result[filename] = target
    emit("materials", files=len(result))
    return result


def main():
    email = os.environ.get("LAT_DEMO_EMAIL", "").strip()
    password = os.environ.get("LAT_DEMO_PASSWORD", "")
    if not email or not password:
        raise CheckFailure("configuration", "credentials_environment_missing")
    api = API(os.environ.get("LAT_API_BASE", "http://127.0.0.1:8000/api/v1"))

    health = api.call("health", "", health=True)
    if not isinstance(health, dict) or health.get("status") != "ok":
        raise CheckFailure("health", "unexpected_health_status")
    emit("health")

    auth = api.call("login", "auth/token/", method="POST",
                    payload={"email": email, "password": password})
    if not isinstance(auth, dict) or not isinstance(auth.get("access"), str):
        raise CheckFailure("login", "access_token_missing")
    api.token = auth["access"]
    # No token or credential is written to disk or included in output.
    password = None
    emit("login")

    profile = api.call("me", "accounts/me/")
    object_id(profile, "me")
    emit("me", profiles=1)

    courses = api.collection("courses", "courses/")
    lessons_count = 0
    exercises_count = 0
    for course in courses:
        course_id = object_id(course, "courses")
        lessons = api.collection("lessons", f"courses/{course_id}/lessons/")
        lessons_count += len(lessons)
        for lesson in lessons:
            lesson_id = object_id(lesson, "lessons")
            exercises_count += len(api.collection(
                "exercises",
                f"courses/{course_id}/lessons/{lesson_id}/exercises/"
            ))
    emit("courses", courses=len(courses))
    emit("lessons", lessons=lessons_count)
    emit("exercises", exercises=exercises_count)

    dashboard = api.call("dashboard", "progress/dashboard/")
    if not isinstance(dashboard, dict) or not isinstance(dashboard.get("courses"), list):
        raise CheckFailure("dashboard", "invalid_dashboard_shape")
    emit("dashboard", courses=len(dashboard["courses"]),
         completed_lessons=sum(
             int(item.get("completed_lessons", 0)) for item in dashboard["courses"]
         ))

    attempts = api.collection("attempts", "progress/attempts/")
    emit("attempts", attempts=len(attempts),
         submitted=sum(a.get("status") == "submitted" for a in attempts),
         checked=sum(a.get("status") == "checked" for a in attempts))

    materials = prepare_materials()
    documents = api.collection("documents", "documents/")
    selected = {}
    created = 0
    reused = 0
    for filename, file_path in materials.items():
        matches = [d for d in documents if d.get("title") == filename]
        if matches:
            # Reuse an existing ready row first; never delete or duplicate a title.
            matches.sort(key=lambda d: (d.get("status") == "ready", d.get("id", 0)),
                         reverse=True)
            selected[filename] = matches[0]
            reused += 1
        else:
            result = api.call("document_upload", "documents/", method="POST",
                              file_path=file_path, timeout=600)
            object_id(result, "document_upload")
            selected[filename] = result
            documents.append(result)
            created += 1
        object_id(selected[filename], "documents")
    emit("document_upload", created=created, reused=reused)

    deadline = time.monotonic() + 180
    while any(d.get("status") in ("uploaded", "processing") for d in selected.values()):
        if time.monotonic() >= deadline:
            raise CheckFailure("documents_ready", "processing_timeout")
        time.sleep(2)
        fresh = {object_id(d, "documents"): d
                 for d in api.collection("documents", "documents/")}
        for filename, current in selected.items():
            selected[filename] = fresh.get(current["id"], current)

    ready = {name: doc for name, doc in selected.items() if doc.get("status") == "ready"}
    failed = sum(d.get("status") == "failed" for d in selected.values())
    emit("documents_ready", "ok" if len(ready) == len(materials) else "failed",
         ready=len(ready), failed=failed, total=len(selected))

    searches = 0
    total_results = 0
    matched_expected = 0
    for filename, query in SEARCHES.items():
        if filename not in ready:
            continue
        found = api.call("semantic_search", "documents/search/", method="POST",
                         payload={"query": query}, timeout=180)
        if not isinstance(found, dict) or not isinstance(found.get("results"), list):
            raise CheckFailure("semantic_search", "invalid_search_shape")
        rows = found["results"]
        if any(not isinstance(row, dict)
               or not isinstance(row.get("content"), str)
               or not isinstance(row.get("distance"), (int, float))
               for row in rows):
            raise CheckFailure("semantic_search", "invalid_result_shape")
        searches += 1
        total_results += len(rows)
        matched_expected += int(any(
            row.get("document_id") == ready[filename]["id"] for row in rows
        ))
    emit("semantic_search",
         "ok" if matched_expected == len(SEARCHES) else "failed",
         queries=searches, results=total_results,
         matched_expected_documents=matched_expected)

    if len(ready) != len(materials):
        raise CheckFailure("verification", "document_processing_failed")
    if matched_expected != len(SEARCHES):
        raise CheckFailure("verification", "expected_documents_not_found")
    emit("verification", material_files=len(materials), search_queries=searches)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CheckFailure as error:
        fields = {"code": error.code}
        if error.http_status is not None:
            fields["http_status"] = error.http_status
        emit(error.stage, "failed", **fields)
        sys.exit(1)
    except (KeyboardInterrupt, BrokenPipeError):
        sys.exit(130)
    except Exception:
        # Keep unexpected failures safe too: no traceback or response data.
        emit("verification", "failed", code="unexpected_local_error")
        sys.exit(1)
