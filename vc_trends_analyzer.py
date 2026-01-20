#!/usr/bin/env python3
"""
VC.ru Trends Analyzer для веб-студий
Анализирует популярные темы на vc.ru и выдает идеи для статей
"""

import requests
import json
from datetime import datetime, timedelta
from collections import Counter
import re
from dataclasses import dataclass
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Для работы без GUI

# Настройка шрифтов для русского языка
plt.rcParams['font.family'] = 'DejaVu Sans'


@dataclass
class Article:
    """Структура данных для статьи"""
    id: int
    title: str
    url: str
    views: int
    likes: int
    comments: int
    date: datetime
    subsite: str
    author: str
    is_promotional: bool = False
    score: float = 0.0


class VCTrendsAnalyzer:
    """Анализатор трендов vc.ru для веб-студий"""

    BASE_URL = "https://api.vc.ru/v2.8"

    # Ключевые слова для поиска веб-тематики
    WEB_KEYWORDS = [
        'сайт', 'веб', 'web', 'разработка', 'дизайн', 'ui', 'ux',
        'лендинг', 'интернет-магазин', 'ecommerce', 'e-commerce', 'маркетплейс',
        'фронтенд', 'frontend', 'бэкенд', 'backend', 'fullstack',
        'react', 'vue', 'angular', 'javascript', 'typescript', 'python',
        'wordpress', 'tilda', 'битрикс', 'bitrix', 'cms', '1с-битрикс',
        'seo', 'конверсия', 'юзабилити', 'usability', 'трафик',
        'мобильная версия', 'адаптив', 'responsive', 'приложени',
        'студия', 'агентство', 'заказчик', 'клиент', 'подрядчик',
        'редизайн', 'рефакторинг', 'техническое задание', 'брендинг',
        'прототип', 'figma', 'макет', 'верстка', 'логотип',
        'api', 'интеграция', 'crm', 'автоматизация', 'бот',
        'хостинг', 'домен', 'ssl', 'безопасность', 'облак',
        'нейросет', 'ai', 'ии', 'искусственный интеллект', 'gpt', 'chatgpt',
        'digital', 'диджитал', 'онлайн', 'it', 'айти', 'стартап',
        'маркетинг', 'продвижени', 'реклам', 'таргет', 'контент',
        'бизнес', 'продаж', 'выручк', 'доход', 'прибыл', 'roi',
        'кейс', 'case', 'проект', 'запуск', 'mvp'
    ]

    # Паттерны продающих статей
    PROMO_PATTERNS = [
        r'как мы', r'наш опыт', r'кейс', r'case', r'история успеха',
        r'увеличили', r'заработали', r'сделали для', r'разработали',
        r'результат', r'roi', r'конверсия выросла', r'привлекли',
        r'наша команда', r'наша студия', r'наше агентство',
        r'обратились к нам', r'клиент пришел', r'заказали у нас'
    ]

    # Subsites (разделы) связанные с веб-разработкой
    RELEVANT_SUBSITES = [
        'design', 'dev', 'marketing', 'seo', 'tech', 'hr',
        'claim', 'tribuna', 'life', 'services', 'finance'
    ]

    def __init__(self, months_back: int = 2):
        """
        Инициализация анализатора

        Args:
            months_back: За сколько месяцев анализировать статьи
        """
        self.months_back = months_back
        self.cutoff_date = datetime.now() - timedelta(days=30 * months_back)
        self.articles: List[Article] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_articles_by_query(self, query: str, count: int = 50) -> List[Dict]:
        """Получает статьи по поисковому запросу"""
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'query': query,
                'order_by': 'relevant',
                'count': count
            }
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                items = data.get('result', {}).get('items', [])
                # Извлекаем статьи из items, API может возвращать разные форматы
                articles = []
                for item in items:
                    if item.get('type') == 'entry':
                        articles.append(item)
                    elif 'data' in item and item['data'].get('type') == 'entry':
                        articles.append(item['data'])
                return articles
        except Exception as e:
            print(f"Ошибка при поиске '{query}': {e}")
        return []

    def fetch_timeline(self, subsite: str = None, count: int = 50,
                       sorting: str = 'hotness') -> List[Dict]:
        """
        Получает статьи из ленты

        Args:
            subsite: Раздел (design, dev, marketing и т.д.)
            count: Количество статей
            sorting: Сортировка (hotness, date, week, month)
        """
        try:
            if subsite:
                url = f"{self.BASE_URL}/subsite/{subsite}/timeline"
            else:
                url = f"{self.BASE_URL}/timeline"

            params = {
                'count': count,
                'sorting': sorting,
                'allSite': 'true' if not subsite else 'false'
            }
            response = self.session.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                items = data.get('result', {}).get('items', [])
                # Извлекаем статьи из вложенных структур
                articles = []
                for item in items:
                    if item.get('type') == 'entry':
                        articles.append(item)
                    elif item.get('type') == 'news':
                        # Внутри news могут быть entry
                        news_items = item.get('data', {}).get('news', [])
                        for news_item in news_items:
                            if news_item.get('type') == 'entry':
                                articles.append(news_item)
                    elif 'data' in item:
                        inner = item['data']
                        if isinstance(inner, dict):
                            if inner.get('type') == 'entry':
                                articles.append(inner)
                return articles
        except Exception as e:
            print(f"Ошибка при получении ленты: {e}")
        return []

    def parse_article(self, raw: Dict) -> Optional[Article]:
        """Парсит сырые данные статьи в объект Article"""
        try:
            # Данные могут быть в разных форматах
            data = raw.get('data', raw)
            if not isinstance(data, dict):
                data = raw

            # Парсим дату
            date_ts = data.get('date', data.get('dateRFC'))
            if isinstance(date_ts, int):
                article_date = datetime.fromtimestamp(date_ts)
            elif isinstance(date_ts, str):
                try:
                    article_date = datetime.fromisoformat(date_ts.replace('Z', '+00:00'))
                except:
                    article_date = datetime.now()
            else:
                article_date = datetime.now()

            # Проверяем, что статья свежая
            if article_date < self.cutoff_date:
                return None

            # Получаем метрики - несколько вариантов где они могут быть
            counters = data.get('counters', {})

            # Likes могут быть в разных местах
            likes_data = data.get('likes', {})
            if isinstance(likes_data, dict):
                likes = likes_data.get('counterLikes', likes_data.get('count', 0))
            else:
                likes = counters.get('likes', 0)

            comments = counters.get('comments', data.get('commentsCount', 0))
            views = counters.get('views', counters.get('hits', data.get('hitsCount', 0)))

            # Subsite
            subsite_data = data.get('subsite', {})
            subsite = subsite_data.get('name', '') if isinstance(subsite_data, dict) else ''

            # Автор
            author_data = data.get('author', {})
            author = author_data.get('name', '') if isinstance(author_data, dict) else ''

            title = data.get('title', '')

            # URL может быть в data или нужно собрать
            url = data.get('url', f"https://vc.ru/{data.get('id', '')}")

            if not title:
                return None

            return Article(
                id=data.get('id', 0),
                title=title,
                url=url,
                views=views or 0,
                likes=likes or 0,
                comments=comments or 0,
                date=article_date,
                subsite=subsite,
                author=author,
                is_promotional=self._is_promotional(title)
            )
        except Exception as e:
            print(f"Ошибка парсинга статьи: {e}")
            return None

    def _is_promotional(self, title: str) -> bool:
        """Определяет, является ли статья продающей"""
        title_lower = title.lower()
        for pattern in self.PROMO_PATTERNS:
            if re.search(pattern, title_lower):
                return True
        return False

    def _is_web_related(self, title: str) -> bool:
        """Проверяет, относится ли статья к веб-тематике"""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self.WEB_KEYWORDS)

    def calculate_score(self, article: Article) -> float:
        """
        Рассчитывает скор статьи для ранжирования

        Формула учитывает:
        - Просмотры (основной вес)
        - Лайки (сильный сигнал качества)
        - Комментарии (вовлеченность)
        - Свежесть (бонус для новых статей)
        - Продающий характер (бонус)
        """
        # Базовые веса
        view_weight = 1.0
        like_weight = 10.0
        comment_weight = 5.0

        # Нормализованные метрики
        views_score = min(article.views / 1000, 100)  # Макс 100 за 100k просмотров
        likes_score = min(article.likes * like_weight, 100)
        comments_score = min(article.comments * comment_weight, 50)

        # Бонус за свежесть (статьи за последнюю неделю)
        days_old = (datetime.now() - article.date).days
        freshness_bonus = max(0, 20 - days_old) if days_old < 20 else 0

        # Бонус за продающий формат
        promo_bonus = 15 if article.is_promotional else 0

        total_score = (
            views_score * view_weight +
            likes_score +
            comments_score +
            freshness_bonus +
            promo_bonus
        )

        return round(total_score, 2)

    def collect_articles(self, verbose: bool = True) -> None:
        """Собирает статьи из разных источников"""
        all_raw_articles = []
        seen_ids = set()

        if verbose:
            print("Сбор статей с vc.ru...")

        # 1. Получаем статьи из общей ленты (hotness и month)
        if verbose:
            print("  Общая лента (популярные)...")

        for sorting in ['hotness', 'month', 'week']:
            results = self.fetch_timeline(None, count=50, sorting=sorting)
            for item in results:
                data = item.get('data', item)
                article_id = data.get('id')
                if article_id and article_id not in seen_ids:
                    seen_ids.add(article_id)
                    all_raw_articles.append(item)

        # 2. Получаем популярные статьи из релевантных разделов
        for subsite in self.RELEVANT_SUBSITES[:5]:  # Ограничим для скорости
            if verbose:
                print(f"  Раздел: {subsite}")

            for sorting in ['month', 'hotness']:
                results = self.fetch_timeline(subsite, count=30, sorting=sorting)
                for item in results:
                    data = item.get('data', item)
                    article_id = data.get('id')
                    if article_id and article_id not in seen_ids:
                        seen_ids.add(article_id)
                        all_raw_articles.append(item)

        # 3. Поиск по ключевым запросам (веб-тематика) - основной источник
        search_queries = [
            'веб-студия', 'разработка сайта', 'веб-разработка',
            'дизайн сайта', 'UI UX дизайн', 'лендинг разработка',
            'интернет-магазин', 'редизайн сайта', 'figma', 'frontend',
            'кейс разработка', 'кейс маркетинг', 'кейс дизайн',
            'digital агентство', 'продвижение сайта', 'SEO оптимизация',
            'конверсия сайта', 'стартап запуск', 'MVP разработка',
            'нейросети бизнес', 'AI маркетинг', 'автоматизация',
            'Tilda сайт', 'WordPress', 'React разработка'
        ]

        for query in search_queries:
            if verbose:
                print(f"  Поиск: {query}")
            results = self.fetch_articles_by_query(query, count=30)
            for item in results:
                data = item.get('data', item)
                article_id = data.get('id')
                if article_id and article_id not in seen_ids:
                    seen_ids.add(article_id)
                    all_raw_articles.append(item)

        if verbose:
            print(f"\nСобрано {len(all_raw_articles)} уникальных статей")

        # Парсим и фильтруем
        web_count = 0
        for raw in all_raw_articles:
            article = self.parse_article(raw)
            if article:
                # Проверяем релевантность веб-тематике
                if self._is_web_related(article.title):
                    article.score = self.calculate_score(article)
                    self.articles.append(article)
                    web_count += 1

        # Сортируем по скору
        self.articles.sort(key=lambda a: a.score, reverse=True)

        # Удаляем дубликаты по заголовку
        unique_articles = []
        seen_titles = set()
        for article in self.articles:
            title_lower = article.title.lower()[:50]
            if title_lower not in seen_titles:
                seen_titles.add(title_lower)
                unique_articles.append(article)
        self.articles = unique_articles

        if verbose:
            print(f"Отфильтровано {len(self.articles)} статей по веб-тематике\n")

    def extract_topic_ideas(self) -> List[Dict]:
        """
        Извлекает идеи для статей из собранных данных

        Возвращает список идей с оценкой потенциала
        """
        ideas = []

        # Анализируем паттерны успешных заголовков
        title_patterns = {
            'кейс': {'count': 0, 'total_score': 0, 'examples': []},
            'как мы': {'count': 0, 'total_score': 0, 'examples': []},
            'ошибки': {'count': 0, 'total_score': 0, 'examples': []},
            'гайд/инструкция': {'count': 0, 'total_score': 0, 'examples': []},
            'тренды': {'count': 0, 'total_score': 0, 'examples': []},
            'сравнение': {'count': 0, 'total_score': 0, 'examples': []},
            'цена/стоимость': {'count': 0, 'total_score': 0, 'examples': []},
            'нейросети/AI': {'count': 0, 'total_score': 0, 'examples': []},
        }

        pattern_rules = {
            'кейс': [r'кейс', r'case', r'история', r'проект'],
            'как мы': [r'как мы', r'наш опыт', r'сделали'],
            'ошибки': [r'ошиб', r'не надо', r'не стоит', r'проблем'],
            'гайд/инструкция': [r'гайд', r'guide', r'инструкция', r'пошагов', r'как сделать', r'чек-лист'],
            'тренды': [r'тренд', r'2024', r'2025', r'2026', r'будущ'],
            'сравнение': [r'vs', r'против', r'сравнени', r'или', r'выбрать'],
            'цена/стоимость': [r'цен', r'стоимость', r'бюджет', r'сколько стоит'],
            'нейросети/AI': [r'нейросет', r'ai', r'ии', r'gpt', r'искусственн'],
        }

        for article in self.articles:
            title_lower = article.title.lower()
            for pattern_name, rules in pattern_rules.items():
                for rule in rules:
                    if re.search(rule, title_lower):
                        title_patterns[pattern_name]['count'] += 1
                        title_patterns[pattern_name]['total_score'] += article.score
                        if len(title_patterns[pattern_name]['examples']) < 3:
                            title_patterns[pattern_name]['examples'].append({
                                'title': article.title,
                                'score': article.score,
                                'url': article.url
                            })
                        break

        # Формируем идеи на основе паттернов
        idea_templates = {
            'кейс': [
                "Кейс: Как мы увеличили конверсию сайта клиента на X%",
                "Кейс: Редизайн интернет-магазина - от старого сайта к современному решению",
                "Кейс: Разработка корпоративного сайта за X дней",
            ],
            'как мы': [
                "Как мы автоматизировали процессы в веб-студии и сократили сроки в 2 раза",
                "Как мы выстроили процесс работы с клиентами без конфликтов",
                "Как мы внедрили AI в рабочие процессы студии",
            ],
            'ошибки': [
                "7 ошибок при заказе сайта, которые стоят бизнесу денег",
                "Почему ваш сайт не продает: разбор типичных ошибок",
                "Ошибки в ТЗ, которые убивают проекты",
            ],
            'гайд/инструкция': [
                "Чек-лист: как подготовить ТЗ для веб-студии",
                "Гайд: как выбрать подрядчика для разработки сайта",
                "Пошаговая инструкция: запуск интернет-магазина с нуля",
            ],
            'тренды': [
                "Тренды веб-дизайна 2026: что будет работать",
                "Какие сайты будут популярны в 2026 году",
                "UI/UX тренды, которые повысят конверсию",
            ],
            'сравнение': [
                "Tilda vs заказная разработка: что выбрать для бизнеса",
                "Сравнение CMS: какую платформу выбрать для интернет-магазина",
                "Фриланс vs студия: плюсы и минусы для заказчика",
            ],
            'цена/стоимость': [
                "Сколько стоит сайт в 2026 году: честный разбор цен",
                "Из чего складывается стоимость разработки сайта",
                "Почему хороший сайт не может стоить дешево",
            ],
            'нейросети/AI': [
                "Как мы используем нейросети в веб-разработке",
                "AI в дизайне: ускоряем работу или убиваем креатив?",
                "Как ChatGPT помогает нам писать код быстрее",
            ],
        }

        for pattern_name, data in title_patterns.items():
            if data['count'] > 0:
                avg_score = data['total_score'] / data['count']
                potential = min(100, avg_score * (1 + data['count'] / 10))

                ideas.append({
                    'category': pattern_name,
                    'potential': round(potential, 1),
                    'popularity': data['count'],
                    'avg_score': round(avg_score, 1),
                    'examples': data['examples'],
                    'suggestions': idea_templates.get(pattern_name, [])
                })

        # Сортируем по потенциалу
        ideas.sort(key=lambda x: x['potential'], reverse=True)

        return ideas

    def visualize_results(self, ideas: List[Dict], output_file: str = 'vc_trends_chart.png') -> None:
        """Создает визуализацию результатов"""
        if not ideas:
            print("Нет данных для визуализации")
            return

        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle('Анализ трендов VC.ru для веб-студии', fontsize=16, fontweight='bold')

        # Данные для графиков
        categories = [idea['category'] for idea in ideas]
        potentials = [idea['potential'] for idea in ideas]
        popularities = [idea['popularity'] for idea in ideas]

        # Цвета
        colors = plt.cm.viridis([i/len(categories) for i in range(len(categories))])

        # График 1: Потенциал тем (горизонтальный бар)
        ax1 = axes[0]
        bars1 = ax1.barh(categories, potentials, color=colors)
        ax1.set_xlabel('Потенциал (0-100)')
        ax1.set_title('Потенциал тем для статей')
        ax1.invert_yaxis()

        # Добавляем значения на бары
        for bar, val in zip(bars1, potentials):
            ax1.text(val + 1, bar.get_y() + bar.get_height()/2,
                    f'{val:.0f}', va='center', fontsize=10)

        # График 2: Популярность (количество статей)
        ax2 = axes[1]
        bars2 = ax2.barh(categories, popularities, color=colors)
        ax2.set_xlabel('Количество найденных статей')
        ax2.set_title('Популярность форматов')
        ax2.invert_yaxis()

        for bar, val in zip(bars2, popularities):
            ax2.text(val + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{val}', va='center', fontsize=10)

        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"📊 График сохранен: {output_file}")
        plt.close()

    def print_recommendations(self, ideas: List[Dict], top_n: int = 10) -> None:
        """Выводит рекомендации по статьям"""
        print("=" * 70)
        print("🎯 ЛУЧШИЕ ИДЕИ ДЛЯ СТАТЕЙ НА VC.RU (веб-студия)")
        print("=" * 70)
        print()

        for i, idea in enumerate(ideas[:top_n], 1):
            print(f"#{i} {idea['category'].upper()}")
            print(f"   Потенциал: {'█' * int(idea['potential']/10)}{'░' * (10 - int(idea['potential']/10))} {idea['potential']}/100")
            print(f"   Найдено статей: {idea['popularity']} | Средний скор: {idea['avg_score']}")
            print()

            if idea['suggestions']:
                print("   💡 Идеи для вашей статьи:")
                for suggestion in idea['suggestions']:
                    print(f"      • {suggestion}")
            print()

            if idea['examples']:
                print("   📝 Примеры успешных статей:")
                for example in idea['examples'][:2]:
                    print(f"      • {example['title'][:60]}...")
                    print(f"        {example['url']} (скор: {example['score']})")
            print()
            print("-" * 70)
            print()

    def print_top_articles(self, top_n: int = 15) -> None:
        """Выводит топ статей для вдохновения"""
        print("\n" + "=" * 70)
        print("🔥 ТОП СТАТЕЙ ДЛЯ ВДОХНОВЕНИЯ")
        print("=" * 70 + "\n")

        for i, article in enumerate(self.articles[:top_n], 1):
            promo_badge = " 💰" if article.is_promotional else ""
            print(f"{i}. {article.title[:65]}...{promo_badge}")
            print(f"   👁 {article.views:,} | 👍 {article.likes} | 💬 {article.comments} | Скор: {article.score}")
            print(f"   📅 {article.date.strftime('%d.%m.%Y')} | {article.url}")
            print()


def main():
    """Главная функция"""
    print("\n" + "=" * 70)
    print("  VC.RU TRENDS ANALYZER для веб-студий")
    print("  Анализ популярных тем за последние 2 месяца")
    print("=" * 70 + "\n")

    # Создаем анализатор
    analyzer = VCTrendsAnalyzer(months_back=2)

    # Собираем статьи
    analyzer.collect_articles(verbose=True)

    if not analyzer.articles:
        print("❌ Не удалось собрать статьи. Проверьте подключение к интернету.")
        return

    # Извлекаем идеи
    ideas = analyzer.extract_topic_ideas()

    # Выводим топ статей
    analyzer.print_top_articles(top_n=15)

    # Выводим рекомендации
    analyzer.print_recommendations(ideas, top_n=8)

    # Создаем визуализацию
    analyzer.visualize_results(ideas, output_file='vc_trends_chart.png')

    print("\n✅ Анализ завершен!")
    print("   - График сохранен в vc_trends_chart.png")
    print("   - Используйте идеи выше для создания продающего контента")


if __name__ == "__main__":
    main()
