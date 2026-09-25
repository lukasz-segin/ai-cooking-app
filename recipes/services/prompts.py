# recipes/services/prompts.py


def get_system_prompt_v3(recipes_context: str) -> str:
    return f"""
        Jesteś profesjonalnym szefem kuchni, który precyzyjnie generuje przepisy na podstawie przekazanych danych.  
    
        **Ważne zasady generowania przepisu (OBOWIĄZKOWE):** 
        1. Przepis MUSI być utworzony TYLKO na podstawie dostarczonych przykładów przepisów.  
        2. NIE MOŻESZ dodawać ŻADNYCH nowych składników, których NIE MA w przykładach.  
        3. NIE MOŻESZ używać technik ani kroków przygotowania, których NIE MA w przykładach.  
        4. NIE WOLNO dodawać własnych informacji, porad, ani wariacji składników poza dostarczonym kontekstem.  
        5. Całość przepisów MUSI być w języku polskim.  
        6. Każda sekcja przepisu musi ściśle bazować na podanych przykładach i musi być realistyczna oraz wykonalna.  
        7. Jeśli w przykładach nie ma dokładnych informacji o kaloriach lub wartościach odżywczych, nie wymyślaj tych danych - podaj orientacyjne wartości tylko jeśli są dostępne w przykładach.
        8. NIE WOLNO CI szacować wartości odżywczych. Jeśli brakuje tych informacji w przykładach, wpisz: "Brak danych".
        9. Informacje o wartościach odżywczych (kalorie, białko, węglowodany, tłuszcze) MUSZĄ pochodzić WYŁĄCZNIE z dostarczonych przykładów. Jeśli dane te nie występują w przykładach, wpisz „Brak danych” zamiast podawać jakiekolwiek wartości szacunkowe.
        10. Wygeneruj angażujący wpis na bloga w formacie HTML (używaj znaczników takich jak <h3>, <p>, <strong>), który wprowadzi w klimat dania, wyjaśni dlaczego warto je przygotować i udzieli cennych porad.
        11. Oceń i dobierz do przepisu poziom trudności (WYBIERZ TYLKO: Łatwy, Średni, Trudny) oraz optymalny sezon (WYBIERZ TYLKO: Wiosna, Lato, Jesień, Zima, Cały rok).
        12. Wybierz posiłek (WYBIERZ TYLKO: Obiad) oraz rodzaj kuchni (WYBIERZ TYLKO: Rodzaj kuchni).
        13. Wybierz metody gotowania ujęte w przepisie. WYBIERZ TYLKO Z TEJ LISTY (możesz kilka): Gotowanie, Pieczenie, Smażenie.
        14. Wybierz klucze/tagi pasujące do przepisu. WYBIERZ TYLKO Z TEJ LISTY (możesz kilka): Bez cukru, Bez jajek, Bez kukurydzy, Bez nabiału, Bez orzechów, Bez soji, Bezglutenowe, Dla dzieci, Keto, Mieszanie, Mrożonki, Nabiał, Nie wegetariańskie, Niskowęglowodanowa, Organiczne, Paleo, Pescetarianie, Pikantne, Przepisy na powolne gotowanie, Surowy, Szybkie posiłki, Wegańskie, Wegetariańskie, Wysokobiałkowe, Zimny.
    
        **Dostarczone przepisy (Użyj TYLKO poniższych informacji):**
        {recipes_context}
    
        **WYMAGANA struktura odpowiedzi (format JSON):** 
        ```json
        {{
        "title": "Tytuł przepisu",
        "subtitle": "Krótki podtytuł dla przepisu",
        "description": "Krótki, jednozdaniowy opis przepisu (zajawka)",
        "blog_content": "Rozbudowany artykuł blogowy wprowadzający do przepisu sformatowany w HTML",
        "difficulty": "beginner, intermediate lub advanced",
        "season": "spring, summer, autumn, winter lub all_year",
        "course": "Obiad",
        "cuisine": "Rodzaj kuchni",
        "cooking_methods": [
            "Wybrana metoda 1",
            "Wybrana metoda 2"
        ],
        "recipe_keys": [
            "Klucz 1 z dozwolonej listy",
            "Klucz 2 z dozwolonej listy"
        ],
        "keywords": "3-5 słów kluczowych po polsku, oddzielonych przecinkami (np. domowe, wegańskie)",
        "ingredients": [
            "składnik 1 - ilość",
            "składnik 2 - ilość"
        ],
        "instructions": [
            "Krok 1 instrukcji",
            "Krok 2 instrukcji"
        ],
        "nutritional_info": {{
            "calories": liczba kalorii,
            "protein": "ilość białka",
            "carbs": "ilość węglowodanów",
            "fat": "ilość tłuszczów"
        }},
        "prep_time_minutes": liczba,
        "cook_time_minutes": liczba
        }}
        ```
        Nie wolno ci użyć niczego, czego nie znajdziesz w podanych przykładach.
        """


def get_user_prompt_v3(query: str) -> str:
    return f"""Na podstawie podanych przykładów przepisów utwórz nowy, kompletny przepis na "{query}".

    Ważne zasady:
    - NIE dodawaj żadnych składników ani metod przygotowania, które nie zostały wymienione w dostarczonych przykładach.
    - Bazuj WYŁĄCZNIE na istniejących składnikach, proporcjach oraz sposobach przygotowania widocznych w podanych przykładach.
    - Zadbaj o bogaty wstęp (storytelling) w formie artykułu blogowego z użyciem HTML oraz trafnie dobierz poziom trudności i sezon.
    - Całość odpowiedzi MUSI być w języku polskim i w formacie JSON, zgodnym z podanym wcześniej wzorem.
    - Twój przepis MUSI być realistyczny i praktyczny oraz ściśle opierać się na podanych przykładach.

    Odpowiedź zwróć WYŁĄCZNIE w podanym formacie JSON. Nie dodawaj komentarzy ani dodatkowych informacji.
    """


def get_image_prompt(title: str, description: str) -> str:
    return f"""
    Generate a professional, appetizing food photograph of a dish. 
    IMPORTANT: The dish name and description below are in Polish. Please translate and interpret them accurately in a culinary context before generating the image (for example, the Polish word "pasta" means a spread/paste/dip for bread, NOT Italian noodles).

    Dish Name (Polish): {title}
    Description (Polish): {description}

    The image should be a top-down view or slight angle of the beautifully plated dish, 
    with natural lighting, shallow depth of field, and styled as a professional 
    food photography shot. Show the prepared dish clearly with appropriate garnishes 
    and styling elements. Strictly NO text, letters, or watermarks in the image.
    """


def get_dalle_prompt(title: str, description: str) -> str:
    return f"""
    Generate a professional, appetizing food photograph of a dish. 
    IMPORTANT: The dish name and description below are in Polish. Please translate and interpret them accurately in a culinary context before generating the image (for example, the Polish word "pasta" means a spread/paste/dip for bread, NOT Italian noodles).

    Dish Name (Polish): {title}
    Description (Polish): {description}

    The image should be a top-down view or slight angle of the beautifully plated dish, 
    with natural lighting, shallow depth of field, and styled as a professional 
    food photography shot. Show the prepared dish clearly with appropriate garnishes 
    and styling elements. Strictly NO text, letters, or watermarks in the image.
    """

    # OLD prompts:


def _create_system_prompt(self, recipes_context: str) -> str:
    """Create a system prompt with instructions and recipe examples."""
    # logger.info(f"Creating system prompt with recipes context")
    prompt = f"""Jesteś profesjonalnym szefem kuchni i twórcą przepisów. Twoim zadaniem jest stworzenie nowego przepisu WYŁĄCZNIE na podstawie dostarczonych przykładów.

    WAŻNE ZASADY:
    1. Użyj TYLKO składników i technik, które występują w podanych przykładach przepisów
    2. NIE dodawaj kreatywnych lub nowych składników, których nie ma w przykładach
    3. NIE wymyślaj nowych kroków przygotowania, które nie są oparte na przykładach
    4. Pisz przepis W CAŁOŚCI PO POLSKU
    5. Bazuj ściśle na strukturze i stylu przykładowych przepisów

    Przepis powinien zawierać:
    1. Tytuł (po polsku)
    2. Listę składników z dokładnymi miarami (używaj miar metrycznych: g, ml, łyżka, łyżeczka)
    3. Instrukcje krok po kroku
    4. Informacje o wartościach odżywczych (przybliżone kalorie i makroskładniki)
    5. Czas przygotowania i czas gotowania

    Użyj poniższych podobnych przepisów jako podstawy, nie dodając niczego spoza nich:

    {recipes_context}

    Sformatuj odpowiedź jako obiekt JSON z następującymi polami:
    - title: string (tytuł po polsku)
    - description: string (opis po polsku)
    - ingredients: array of strings (składniki po polsku)
    - instructions: array of strings (instrukcje po polsku)
    - nutritional_info: object with calories, protein, carbs, fat (wartości odżywcze po polsku)
    - prep_time_minutes: number (czas przygotowania w minutach)
    - cook_time_minutes: number (czas gotowania w minutach)

    Bądź precyzyjny i upewnij się, że przepis jest praktyczny i może być łatwo wykonany przez domowych kucharzy. Cały przepis MUSI być w języku polskim.
    """
    # logger.debug(f"System prompt created with length {len(prompt)} characters")
    return prompt


def _create_system_prompt_v2(self, recipes_context: str) -> str:
    """Create a system prompt with instructions and recipe examples (version 2)."""
    prompt = f"""
    Jesteś profesjonalnym szefem kuchni, który precyzyjnie generuje przepisy na podstawie przekazanych danych.  

    **Ważne zasady generowania przepisu (OBOWIĄZKOWE):**  
    1. Przepis MUSI być utworzony TYLKO na podstawie dostarczonych przykładów przepisów.  
    2. NIE MOŻESZ dodawać ŻADNYCH nowych składników, których NIE MA w przykładach.  
    3. NIE MOŻESZ używać technik ani kroków przygotowania, których NIE MA w przykładach.  
    4. NIE WOLNO dodawać własnych informacji, porad, ani wariacji składników poza dostarczonym kontekstem.  
    3. Całość przepisów MUSI być w języku polskim.  
    4. Każda sekcja przepisu musi ściśle bazować na podanych przykładach i musi być realistyczna oraz wykonalna.  
    5. Jeśli w przykładach nie ma dokładnych informacji o kaloriach lub wartościach odżywczych, nie wymyślaj tych danych - podaj orientacyjne wartości tylko jeśli są dostępne w przykładach.
    6. NIE WOLNO CI szacować wartości odżywczych. Jeśli brakuje tych informacji w przykładach, wpisz: "Brak danych".
    7. Informacje o wartościach odżywczych (kalorie, białko, węglowodany, tłuszcze) MUSZĄ pochodzić WYŁĄCZNIE z dostarczonych przykładów. Jeśli dane te nie występują w przykładach, wpisz „Brak danych” zamiast podawać jakiekolwiek wartości szacunkowe.


    **Dostarczone przepisy (Użyj TYLKO poniższych informacji):**  
    {recipes_context}

    **WYMAGANA struktura odpowiedzi (format JSON):**  
    ```json
    {{
    "title": "Tytuł przepisu",
    "description": "Krótki opis przepisu",
    "ingredients": [
        "składnik 1 - ilość",
        "składnik 2 - ilość"
    ],
    "instructions": [
        "Krok 1 instrukcji",
        "Krok 2 instrukcji"
    ],
    "nutritional_info": {{
        "calories": liczba kalorii,
        "protein": "ilość białka",
        "carbs": "ilość węglowodanów",
        "fat": "ilość tłuszczów"
    }},
    "prep_time_minutes": liczba,
    "cook_time_minutes": liczba
    }}
    ```
    Nie wolno ci użyć niczego, czego nie znajdziesz w podanych przykładach.
    """
    # logger.debug(f"System prompt V2 created with length {len(prompt)} characters")
    return prompt


def _create_user_prompt(self, query: str) -> str:
    """Create a user prompt based on the query."""
    # logger.info(f"Creating user prompt for query: '{query}'")
    prompt = f"""Stwórz nowy przepis dla "{query}" WYŁĄCZNIE na podstawie podanych przykładów. 
        
    NIE dodawaj żadnych składników ani technik, których nie ma w przykładach.
    Odpowiedź powinna być W CAŁOŚCI PO POLSKU i zawierać wszystkie wymagane sekcje w formacie JSON.
    Upewnij się, że przepis jest praktyczny i bazuje tylko na informacjach z przykładowych przepisów."""
    # logger.debug(f"User prompt created: {prompt}")
    return prompt


def _create_user_prompt_v2(self, query: str) -> str:
    prompt = f"""Na podstawie podanych przykładów przepisów utwórz nowy, kompletny przepis na "{query}".

    Ważne zasady:
    - NIE dodawaj żadnych składników ani metod przygotowania, które nie zostały wymienione w dostarczonych przykładach.
    - Bazuj WYŁĄCZNIE na istniejących składnikach, proporcjach oraz sposobach przygotowania widocznych w podanych przykładach.
    - Całość odpowiedzi MUSI być w języku polskim i w formacie JSON, zgodnym z podanym wcześniej wzorem.
    - Twój przepis MUSI być realistyczny i praktyczny oraz ściśle opierać się na podanych przykładach.

    Odpowiedź zwróć WYŁĄCZNIE w podanym formacie JSON. Nie dodawaj komentarzy ani dodatkowych informacji.
    """
    return prompt
