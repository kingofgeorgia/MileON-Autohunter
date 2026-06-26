const backendBaseUrl = 'http://127.0.0.1:8000';

const form = document.getElementById('calculator-form');
const resultBox = document.getElementById('result-box');
const parseButton = document.getElementById('parse-link');
const urlInput = document.getElementById('source-url');

const setResult = (payload) => {
  resultBox.innerHTML = `
    <div class="summary-card">
      <h3>Итоговая стоимость</h3>
      <div class="price">${payload.total_cost.toLocaleString('ru-RU')} ₽</div>
      <div class="details-grid">
        <div><span>Таможня</span><strong>${payload.customs_duty.toLocaleString('ru-RU')} ₽</strong></div>
        <div><span>НДС</span><strong>${payload.vat.toLocaleString('ru-RU')} ₽</strong></div>
        <div><span>Логистика</span><strong>${payload.logistics_cost.toLocaleString('ru-RU')} ₽</strong></div>
        <div><span>Брокер</span><strong>${payload.broker_fee.toLocaleString('ru-RU')} ₽</strong></div>
      </div>
      <p>${payload.comparison_note}</p>
    </div>
  `;
};

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(form).entries());

  const requestBody = {
    car_price: Number(payload.car_price),
    engine_volume: Number(payload.engine_volume || 2),
    engine_power: Number(payload.engine_power || 180),
    year: Number(payload.year || 2018),
    fuel_type: payload.fuel_type || 'petrol',
    customs_rate: Number(payload.customs_rate || 0.4),
    logistics_cost: Number(payload.logistics_cost || 0),
    broker_fee: Number(payload.broker_fee || 0),
    registration_cost: Number(payload.registration_cost || 0),
    currency: 'RUB',
    source_url: payload.source_url || null,
  };

  resultBox.innerHTML = '<div class="summary-card loading">Рассчитываем…</div>';

  try {
    const response = await fetch(`${backendBaseUrl}/api/calculator/estimate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    });

    const data = await response.json();
    if (data.result) {
      setResult(data.result);
    } else {
      resultBox.innerHTML = '<div class="summary-card error">Ошибка расчёта</div>';
    }
  } catch (error) {
    resultBox.innerHTML = '<div class="summary-card error">Не удалось связаться с backend</div>';
  }
});

parseButton.addEventListener('click', async () => {
  const url = urlInput.value.trim();
  if (!url) return;

  try {
    const response = await fetch(`${backendBaseUrl}/api/calculator/parse-myauto`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const data = await response.json();
    const hint = document.getElementById('parse-hint');
    hint.textContent = data.result?.listing_id ? `Обнаружен ID: ${data.result.listing_id}` : 'Ссылка не распознана';
  } catch (error) {
    const hint = document.getElementById('parse-hint');
    hint.textContent = 'Не удалось распознать ссылку';
  }
});
