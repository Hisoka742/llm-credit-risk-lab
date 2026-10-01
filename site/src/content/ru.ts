// Russian versions of strings that reach the page from the study's data files (study.json),
// where they exist in English only. Borrower descriptions and the LLM's JSON are evidence and
// are never translated.

export const EXPERIMENT_LABEL_RU: Record<string, string> = {
  e0: "Табличная базовая модель",
  e1: "Табличные + эмбеддинги",
  e2: "Табличные + признаки LLM",
  e3: "Табличные + эмбеддинги + LLM",
  e4: "Только текст (TF-IDF)",
};

/** Reasons from src/features/leakage.py, keyed by the English reason. */
export const LEAKAGE_REASON_RU: Record<string, string> = {
  "payments received to date": "платежи, полученные к дате выгрузки",
  "payments received to date (investor share)": "платежи, полученные к дате выгрузки (доля инвесторов)",
  "principal received to date": "погашенный основной долг к дате выгрузки",
  "interest received to date": "полученные проценты к дате выгрузки",
  "late fees received, only non-zero if the borrower was late":
    "штрафы за просрочку: не равны нулю, только если заёмщик опаздывал с платежом",
  "post charge-off recoveries, non-zero only for defaults":
    "взыскания после списания: не равны нулю только у дефолтных кредитов",
  "post charge-off collection fee": "комиссия за взыскание после списания",
  "outstanding principal at snapshot": "остаток основного долга на дату выгрузки",
  "outstanding principal at snapshot (investor share)": "остаток основного долга на дату выгрузки (доля инвесторов)",
  "date of last payment": "дата последнего платежа",
  "amount of last payment": "сумма последнего платежа",
  "next scheduled payment, empty once the loan is closed": "следующий плановый платёж: пусто, когда кредит закрыт",
  "date of most recent bureau pull (servicing)": "дата последнего запроса в бюро (сопровождение кредита)",
  "refreshed FICO after issuance, collapses on default": "обновлённый после выдачи FICO: резко падает при дефолте",
  "investor-funded amount, finalized after listing closes":
    "сумма, профинансированная инвесторами: известна после закрытия заявки",
  "payment plan flag set during servicing": "признак плана платежей, который ставится при сопровождении",
  "hardship program": "программа помощи заёмщикам в трудной ситуации",
  "hardship program (no prefix)": "программа помощи заёмщикам (поле без общего префикса)",
  "debt settlement after default": "урегулирование долга после дефолта",
};

/** Manual review notes for the pilot listings, keyed by loan id. */
export const REVIEW_NOTE_RU: Record<string, string> = {
  "709197": "Два слова не несут сигнала, и модель так и отвечает: text_quality 1.",
  "5365409": "Стресс 3 за потерю, которая уже в прошлом.",
  "200256":
    "Стресс и семейные обстоятельства определены верно. Занятость 1 (нестабильная) в тексте не указана: сказано только, что работа — единственный доход.",
  "2086642": "Кредитные карты, двенадцать лет на одной работе, изложенный план.",
  "1020958":
    "Кредит берут на свадьбу. Модель зацепилась за упомянутый вскользь студенческий заём и ответила education.",
  "1583722":
    "Работа не упомянута, а employment_stability вернулась 3. Модель приняла аккуратную платёжную историю за стабильную занятость.",
  "3526633": "Заёмщик объясняет, что вернёт долг с продажи годовалых лошадей, но has_repayment_plan равен false.",
  "8394629":
    "В тексте сказано: консолидация кредитных карт. По правилу из самого промпта это должно быть credit_card.",
  "642370": "Пять лет у одного работодателя и расписанный бюджет — и то и другое учтено.",
};

export const MONTHS_RU = ["янв.", "февр.", "март", "апр.", "май", "июнь", "июль", "авг.", "сент.", "окт.", "нояб.", "дек."];
