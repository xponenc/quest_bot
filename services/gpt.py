from openai import AsyncOpenAI

from services.db_process import get_game_context
from services.loggers import logger


# Функция генерации старта новой игры
async def gpt_create_new_game(genre: str = ""):
    system_prompt = """Ты профессиональный сценарист и дизайнер компьютерных игр.
    Придумай сюжет ролевой игры, выдай краткий сценарий и предложи пользователю первый шаг описав выбор 
    и предоставь три варианта действий. Обильно используй в тексте эмодзи, добавляй их внутри предложения по смыслу.
    # Обязательно укажи ЦЕЛЬ ИГРЫ
    Ответ выдай в формате доступном для обработки json.loads. Используй следующую структуру в ответе:
    {
      "game_name": "Название игры",
      "story": "Сюжет",
      "stage_description": "Описание ситуации перед шагом пользователя"
      "options_of_moves": {
        "1": {
          "description": "Описание первой сюжетной линии",
          "outcome_hint": "Подсказки для первой сюжетной линии"
        },
        ...
      }
    }
    """
    if genre:
        user_prompt = f"Игра должна быть в жанре {genre}"
    else:
        user_prompt = f"Жанр игры придумай тоже сам"
    logger.info(f"Start create new game")
    logger.info(f"System prompt: {system_prompt}")
    logger.info(f"User prompt: {user_prompt}")

    # Используем await для асинхронного вызова
    games_data, price, tokens_info = await get_response_openai(system_prompt, user_prompt)
    logger.info(tokens_info)

    # Возвращаем структуру и информацию о токенах
    return games_data, price, tokens_info


# Функция генерации старта новой игры
async def gpt_create_new_stage(telegram_id: int, game_id: int):
    game_context = await get_game_context(telegram_id=telegram_id, game_id=game_id)

    system_prompt = """Ты профессиональный сценарист и дизайнер компьютерных игр.
    Ты получишь данные описывающие игру, которую ты ведешь с пользователем: ее описание и этапы.
    Проанализируй ход игры и для последнего этапа в соответствии с выбором игрока придумай следующий ход в соответствии
     с сюжетом и целью игры.
    Ты можешь сгенерировать следующий ход как вопрос игроку от имени встреченного персонажа или 
    краткое описание ситуации и три варианта хода. Ответ выдай в формате доступном для обработки json.loads.
    Если следующий ход - вопрос, то выдай ответ в виде:
    {"question": "Текст вопроса"
    Если следующий ход - описание ситуации и три варианта ответа, то выдай ответ в форме:
     Используй следующую структуру в ответе:
    {
      "stage_description": "Описание ситуации перед шагом пользователя"
      "options_of_moves": {
        "1": {
          "description": "Описание первой сюжетной линии",
          "outcome_hint": "Подсказки для первой сюжетной линии"
        },
        ...
      }
    }
    """
    system_prompt += f"\nИГРА: {game_context}"
    user_prompt = f"Придумай следующий ход"
    logger.info(f"Start create new stage for {game_id}")
    logger.info(f"System prompt: {system_prompt}")
    logger.info(f"User prompt: {user_prompt}")

    # Используем await для асинхронного вызова
    stage_data, price, tokens_info = await get_response_openai(system_prompt, user_prompt)
    logger.info(tokens_info)
    # Возвращаем структуру и информацию о токенах
    return stage_data, price, tokens_info


# Функция подсчета токенов и стоимости
def tokens_count_and_price(completion, model='gpt-4o-mini'):
    if model == "gpt-4o-mini":
        input_price, output_price = 0.15 * 100, 0.60 * 100  # Переводим в рубли
    elif model == "gpt-4o":
        input_price, output_price = 5 * 100, 15 * 100  # Переводим в рубли
    else:
        raise ValueError("Неверная модель. Доступные модели: gpt-4o, gpt-4o-mini")

    price = (input_price * completion.usage.prompt_tokens /
             1e6 + output_price * completion.usage.completion_tokens / 1e6)
    return price, (f"\nTokens used: {completion.usage.prompt_tokens} + {completion.usage.completion_tokens} "
                   f"= {completion.usage.total_tokens}. Model: {model}, Price: {round(price, 2)} руб.")


# Функция для запроса и получения ответа от OpenAI с использованием chat моделей
async def get_response_openai(system_prompt, user_prompt, model='gpt-4o-mini', temp=0., max_tokens=4096):
    # Используем асинхронный вызов OpenAI API
    response = await AsyncOpenAI().chat.completions.create(
        model=model,
        temperature=temp,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    price, tokens_info = tokens_count_and_price(response, model)
    logger.info(f"GPT answer: {response}")
    return response.choices[
        0].message.content, price, tokens_info  # Возвращаем три значения: контент, цену и информацию о токенах
