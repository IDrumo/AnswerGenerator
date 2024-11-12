import os
import random
import re
import tkinter as tk
import zipfile
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

import numpy as np


class Question:
    def __init__(self, number, text, options, correct_indices):
        self.number = number
        self.text = text
        self.options = options
        self.correct_indices = correct_indices

    def __repr__(self):
        return f"Question({self.number}, {self.text}, {self.options}, {self.correct_indices})"


class QuestionAnswerFile:
    def __init__(self, filename):
        self.filename = filename
        self.questions = {}
        self.load_file()

    def load_file(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            current_question = None
            question_number = 0

            for line in lines:
                line = line.strip()

                # Проверка на начало нового вопроса
                question_match = re.match(r'^\d+\.\s', line)
                if question_match:
                    # Если был предыдущий вопрос, добавляем его
                    if current_question is not None:
                        self.questions[question_number] = current_question

                    # Увеличиваем номер вопроса
                    question_number += 1

                    # Создаем новую структуру вопроса
                    current_question = Question(
                        number=question_number,
                        text=line[question_match.end():],
                        options=[],
                        correct_indices=[]
                    )
                elif current_question is not None:
                    # Обработка вариантов ответов
                    if line.startswith('+'):
                        # Верный ответ
                        current_question.options.append(line[1:].strip())
                        current_question.correct_indices.append(
                            len(current_question.options) - 1
                        )
                    elif line:
                        # Обычный вариант ответа
                        current_question.options.append(line.strip())

            # Добавляем последний вопрос
            if current_question is not None:
                self.questions[question_number] = current_question

    def print_questions(self):
        for question in self.questions.values():
            print(f"Вопрос {question.number}: {question.text}")
            print("Варианты:")
            for j, opt in enumerate(question.options, 1):
                marker = " ✓" if j - 1 in question.correct_indices else ""
                print(f"  {j}. {opt}{marker}")
            print()


class StudentFile:
    def __init__(self, filename):
        self.filename = filename
        self.students = []
        self.load_file()

    def load_file(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            self.students = f.readlines()
            for i in range(len(self.students)):
                self.students[i] = self.students[i].strip()


class StudentAnswer:
    def __init__(self, student_name):
        self.student_name = student_name
        self.answers = {}  # Словарь с вопросами и их ответами
        self.error_count = 0
        self.error_questions = []  # Список номеров вопросов с ошибками

    def add_answer(self, question_number, answer):
        self.answers[question_number] = answer

    def increment_error_count(self):
        self.error_count += 1

    def add_error_question(self, question_number):
        self.error_questions.append(question_number)

    def __repr__(self):
        return f"StudentAnswer({self.student_name}, {self.error_count}, {self.error_questions})"


class AnswerGenerator:
    def __init__(self, question_answer_file, student_file):
        self.question_answer_file = question_answer_file
        self.student_file = student_file
        self.students_answers = {}

    def generate_student_answers(self, max_errors):
        # Очищаем предыдущие результаты
        self.students_answers.clear()

        for student in self.student_file.students:
            student_answer = StudentAnswer(student)  # Создаем экземпляр StudentAnswer для каждого студента

            # Генерируем количество ошибок по нормальному распределению
            num_errors = self._generate_errors(max_errors)

            # Копируем структуру вопросов и ответов
            student_answer.answers = self.question_answer_file.questions.copy()

            # Выбираем случайные вопросы для ошибок
            error_indices = random.sample(
                range(len(self.question_answer_file.questions)),
                min(num_errors, len(self.question_answer_file.questions))
            )

            # Вносим ошибки
            for idx in error_indices:
                question_number = idx + 1  # +1, так как ключи начинаются с 1
                current_question = self.question_answer_file.questions[question_number]
                total_options = len(current_question.options)
                correct_indices = current_question.correct_indices

                # Генерируем список неправильных индексов
                wrong_indices = [i for i in range(total_options) if i not in correct_indices]

                # Если есть неправильные ответы, заменяем правильные ответы на случайные неправильные
                if wrong_indices:
                    student_answer.increment_error_count()
                    student_answer.add_error_question(question_number)

                    # Заменяем каждый правильный ответ на случайный неправильный
                    student_answer.answers[question_number].correct_indices = [
                        random.choice(wrong_indices) for _ in correct_indices
                    ]

            # Сохраняем результаты для студента
            self.students_answers[student] = student_answer

    def _generate_errors(self, max_errors):
        """
        Генерация количества ошибок по нормальному распределению
        """
        # Используем усеченное нормальное распределение
        while True:
            # Среднее = max_errors / 2, стандартное отклонение = max_errors / 4
            errors = int(np.random.normal(
                loc=max_errors / 2,
                scale=max_errors / 4
            ))

            # Ограничиваем количество ошибок
            if 0 <= errors <= max_errors:
                return errors

    def create_student_answer_files(self, output_dir):
        """
        Создание файлов ответов для каждого студента
        """
        # Создаем директорию, если она не существует
        os.makedirs(output_dir, exist_ok=True)

        for student, data in self.students_answers.items():
            # Формируем путь к файлу
            filename = os.path.join(output_dir, f"{student}_answers.txt")

            with open(filename, 'w', encoding='utf-8') as f:
                # Итерация по всем вопросам
                for question_number in range(1, len(data.answers) + 1):
                    question = data.answers[question_number]

                    # Записываем номер вопроса и текст вопроса
                    f.write(f"{question.number}. {question.text}\n")

                    # Получаем индексы ответов студента для текущего вопроса
                    # answer_indices = data.answers.get(question_number, [])
                    answer_indices = question.correct_indices

                    # Записываем все ответы, соответствующие индексам
                    answers_to_write = [question.options[i] for i in answer_indices if i < len(question.options)]
                    f.write("\n".join(answers_to_write) + "\n")  # Записываем ответы, каждый на новой строке

                    # Добавляем пустую строку-разделитель
                    f.write("\n")

                #     # Добавляем информацию о количестве ошибок, если они есть
                #     if question_number in data.error_questions:
                #         f.write("Ошибка: Да\n")
                #     else:
                #         f.write("Ошибка: Нет\n")
                #
                # # Записываем общее количество ошибок
                # f.write(f"Общее количество ошибок: {data.error_count}\n")


# Все предыдущие классы остаются без изменений

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Question Answer Application")
        self.geometry("700x700")

        self.question_answer_file = None
        self.student_file = None
        self.answer_generator = None
        self.generated_files = {}  # Словарь для хранения сгенерированных файлов

        self.create_widgets()

    def create_widgets(self):
        self.question_frame = ttk.LabelFrame(self, text="Question and Answer File")
        self.question_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.student_frame = ttk.LabelFrame(self, text="Student File")
        self.student_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.answer_frame = ttk.LabelFrame(self, text="Answers")
        self.answer_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.load_question_button = ttk.Button(
            self.question_frame,
            text="Load Questions",
            command=self.load_question_file
        )
        self.load_question_button.pack(pady=5)

        self.load_student_button = ttk.Button(
            self.student_frame,
            text="Load Students",
            command=self.load_student_file
        )
        self.load_student_button.pack(pady=5)

        # Поле для ввода максимального количества ошибок
        self.errors_frame = ttk.LabelFrame(self, text="Error Settings")
        self.errors_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.max_errors_label = ttk.Label(self.errors_frame, text="Max Errors:")
        self.max_errors_label.pack(side=tk.LEFT, padx=5, pady=5)

        self.max_errors_entry = ttk.Entry(self.errors_frame, width=10)
        self.max_errors_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.max_errors_entry.insert(0, "0")  # значение по умолчанию

        # Кнопка генерации ответов для студентов
        self.generate_student_answers_button = ttk.Button(
            self.answer_frame,
            text="Generate Student Answers",
            command=self.generate_student_answers
        )
        self.generate_student_answers_button.pack(pady=5)

        # Кнопка создания ZIP архива
        self.create_zip_button = ttk.Button(
            self.answer_frame,
            text="Create ZIP Archive",
            command=self.create_zip_archive
        )
        self.create_zip_button.pack(pady=5)

        # Текстовое поле для вывода результатов
        self.result_text = tk.Text(self.answer_frame, height=15, width=70)
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

    def load_question_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            self.question_answer_file = QuestionAnswerFile(file_path)

    def load_student_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            self.student_file = StudentFile(file_path)

    def generate_student_answers(self):
        if not (self.question_answer_file and self.student_file):
            messagebox.showerror("Error", "Load question and student files first!")
            return

        try:
            max_errors = int(self.max_errors_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid max errors value!")
            return

        # Создаем генератор ответов
        self.answer_generator = AnswerGenerator(
            self.question_answer_file,
            self.student_file
        )

        # Генерируем ответы
        self.answer_generator.generate_student_answers(max_errors)

        # Очищаем предыдущие результаты
        self.result_text.delete(1.0, tk.END)
        self.generated_files.clear()

        # Временная директория для хранения файлов
        temp_dir = os.path.join(os.getcwd(), "temp_student_answers")
        os.makedirs(temp_dir, exist_ok=True)

        # Создаем файлы ответов для каждого студента
        self.answer_generator.create_student_answer_files(temp_dir)

        # Сохраняем информацию о сгенерированных файлах
        for student, data in self.answer_generator.students_answers.items():
            self.generated_files[student] = os.path.join(temp_dir, f"{student}_answers.txt")

            # Подсчет правильных ответов и получение номеров вопросов с ошибками
            correct_answers, error_questions = self.count_correct_answers(data)

            # Выводим результат в текстовое поле
            self.result_text.insert(
                tk.END,
                f"{student}: {correct_answers}/{len(self.answer_generator.question_answer_file.questions)} "
                f"(Errors: {data.error_count}, Error Questions: {error_questions})\n"
            )

    def create_zip_archive(self):
        if not self.generated_files:
            messagebox.showerror("Error", "Generate student answers first!")
            return

        # Выбираем директорию для сохранения ZIP
        zip_filename = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip")]
        )

        if zip_filename:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for student, filepath in self.generated_files.items():
                    zipf.write(filepath, os.path.basename(filepath))

            messagebox.showinfo(
                "Success",
                f"Created ZIP archive with {len(self.generated_files)} student answer files"
            )

    def count_correct_answers(self, student_answer):
        total_questions = len(self.question_answer_file.questions)
        correct_count = total_questions - student_answer.error_count  # Количество правильных ответов
        error_questions = student_answer.error_questions  # Номера вопросов с ошибками

        return correct_count, error_questions


if __name__ == "__main__":
    app = Application()
    app.mainloop()