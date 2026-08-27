let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();
let selectedMood = 5;
let userData = null;
let API_BASE = '';

document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    initCursorTrail();
    loadData();
    renderCalendar();
    initReviews();
});

function getApiBase() {
    if (API_BASE) return API_BASE;
    const loc = window.location;
    API_BASE = loc.protocol + '//' + loc.hostname + (loc.port ? ':' + loc.port : '');
    return API_BASE;
}

function getUserId() {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        return tg.initDataUnsafe.user.id;
    }
    const params = new URLSearchParams(window.location.search);
    return params.get('user_id');
}

// ═══════ PARTICLES ═══════
function initParticles() {
    const c = document.getElementById('particles');
    if (!c) return;
    for (let i = 0; i < 30; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = (5 + Math.random() * 10) + 's';
        p.style.animationDelay = Math.random() * 5 + 's';
        const s = (1 + Math.random() * 2) + 'px';
        p.style.width = s; p.style.height = s;
        c.appendChild(p);
    }
}

// ═══════ CURSOR ═══════
function initCursorTrail() {
    const t = document.getElementById('cursorTrail');
    if (!t) return;
    let mx = 0, my = 0, tx = 0, ty = 0;
    document.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });
    document.addEventListener('touchmove', e => { mx = e.touches[0].clientX; my = e.touches[0].clientY; });
    (function a() { tx += (mx - tx) * 0.1; ty += (my - ty) * 0.1; t.style.left = tx + 'px'; t.style.top = ty + 'px'; requestAnimationFrame(a); })();
}

// ═══════ TABS ═══════
function switchTab(name) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelector('[data-tab="' + name + '"]').classList.add('active');
    document.getElementById(name).classList.add('active');
    if (name === 'calendar') renderCalendar();
    if (name === 'chart') renderChart();
}

// ═══════ LOAD DATA ═══════
function loadData() {
    const tg = window.Telegram && window.Telegram.WebApp;
    if (tg) { try { tg.ready(); tg.expand(); } catch(e) {} }

    const uid = getUserId();
    if (uid) {
        fetch(getApiBase() + '/api/user/' + uid)
            .then(r => r.json())
            .then(data => {
                userData = transformData(data);
                updateUI();
                renderCalendar();
            })
            .catch(e => {
                console.error(e);
                userData = emptyData();
                updateUI();
            });
    } else {
        userData = emptyData();
        updateUI();
    }
}

function emptyData() {
    return {
        userId: null,
        goal: null,
        allGoals: [],
        logs: {},
        streak: 0,
        bestStreak: 0,
        totalEarned: 0,
        activeDays: 0,
        wish: null,
        thoughts: [],
        unit: 'руб'
    };
}

function transformData(data) {
    const result = {
        userId: data.user ? data.user.user_id : null,
        goal: null,
        allGoals: data.all_goals || [],
        logs: {},
        streak: data.streak ? data.streak.current_streak : 0,
        bestStreak: data.streak ? data.streak.best_streak : 0,
        totalEarned: data.total_earned || 0,
        activeDays: data.active_days || 0,
        wish: data.wish ? data.wish.wish_text : null,
        thoughts: data.thoughts || [],
        unit: 'руб'
    };

    if (data.goal) {
        result.goal = {
            id: data.goal.id,
            title: data.goal.title,
            target: data.goal.target_value || 0,
            current: data.goal.current_value || 0,
            unit: data.goal.unit || 'руб',
            deadline: data.goal.deadline
        };
        result.unit = data.goal.unit || 'руб';
    }

    if (data.logs) {
        data.logs.forEach(log => {
            result.logs[log.log_date] = {
                earned: log.earned,
                mood: log.mood,
                note: log.note
            };
        });
    }

    return result;
}

// ═══════ UPDATE UI ═══════
function updateUI() {
    if (!userData) return;

    document.getElementById('streakCount').textContent = userData.streak;

    if (userData.goal) {
        const g = userData.goal;
        const pct = g.target > 0 ? (g.current / g.target * 100) : 0;

        document.getElementById('goalTitle').textContent = g.title;
        document.getElementById('goalSubtitle').textContent = g.current.toLocaleString() + ' из ' + g.target.toLocaleString() + ' ' + g.unit;
        document.getElementById('progressFill').style.width = Math.min(pct, 100) + '%';
        document.getElementById('progressCurrent').textContent = g.current.toLocaleString();
        document.getElementById('progressTarget').textContent = g.target.toLocaleString();
        document.getElementById('progressUnit').textContent = g.unit;
        document.getElementById('progressPercentage').textContent = pct.toFixed(1) + '%';

        if (g.deadline) {
            const dl = new Date(g.deadline);
            const now = new Date();
            const days = Math.ceil((dl - now) / 86400000);
            document.getElementById('daysLeft').textContent = days > 0 ? days : 'Срок вышел';
            if (days > 0 && g.target > g.current) {
                document.getElementById('perDay').textContent = Math.ceil((g.target - g.current) / days).toLocaleString() + ' ' + g.unit;
            }
        }
    } else {
        document.getElementById('goalTitle').textContent = 'Нет активной цели';
        document.getElementById('goalSubtitle').textContent = 'Создай цель через бота (/goal)';
        document.getElementById('progressFill').style.width = '0%';
        document.getElementById('progressCurrent').textContent = '0';
        document.getElementById('progressTarget').textContent = '0';
        document.getElementById('progressPercentage').textContent = '0%';
        document.getElementById('daysLeft').textContent = '—';
        document.getElementById('perDay').textContent = '—';
    }

    document.getElementById('totalEarned').textContent = userData.totalEarned.toLocaleString();
    document.getElementById('activeDays').textContent = userData.activeDays;
    document.getElementById('bestStreak').textContent = userData.bestStreak;
    const avg = userData.activeDays > 0 ? Math.round(userData.totalEarned / userData.activeDays) : 0;
    document.getElementById('avgPerDay').textContent = avg.toLocaleString();

    if (userData.goal && userData.goal.target > 0) {
        const totalBar = (userData.totalEarned / userData.goal.target * 100);
        document.getElementById('totalBar').style.width = Math.min(totalBar, 100) + '%';
    }

    if (userData.wish) {
        document.getElementById('wishCard').style.display = 'block';
        document.getElementById('wishText').textContent = '"' + userData.wish + '"';
    } else {
        document.getElementById('wishCard').style.display = 'none';
    }

    renderChart();
}

// ═══════ CALENDAR ═══════
function renderCalendar() {
    const months = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
    document.getElementById('calMonth').textContent = months[currentMonth] + ' ' + currentYear;
    const first = new Date(currentYear, currentMonth, 1);
    const last = new Date(currentYear, currentMonth + 1, 0);
    const start = (first.getDay() + 6) % 7;
    const c = document.getElementById('calendarDays');
    c.innerHTML = '';
    const today = new Date().toISOString().split('T')[0];
    for (let i = 0; i < start; i++) { const d = document.createElement('div'); d.className = 'cal-day empty'; c.appendChild(d); }
    for (let day = 1; day <= last.getDate(); day++) {
        const d = document.createElement('div');
        d.className = 'cal-day';
        d.textContent = day;
        const ds = currentYear + '-' + String(currentMonth + 1).padStart(2, '0') + '-' + String(day).padStart(2, '0');
        if (ds === today) d.classList.add('today');
        if (userData && userData.logs[ds]) { d.classList.add('checked'); d.onclick = () => showDayDetail(ds); }
        c.appendChild(d);
    }
}
function prevMonth() { currentMonth--; if (currentMonth < 0) { currentMonth = 11; currentYear--; } renderCalendar(); }
function nextMonth() { currentMonth++; if (currentMonth > 11) { currentMonth = 0; currentYear++; } renderCalendar(); }

function showDayDetail(ds) {
    const log = userData.logs[ds];
    if (!log) return;
    const d = new Date(ds);
    const dn = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
    const mn = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
    document.getElementById('detailDate').textContent = dn[d.getDay()] + ', ' + d.getDate() + ' ' + mn[d.getMonth()];
    document.getElementById('detailEarned').textContent = log.earned.toLocaleString() + ' ' + userData.unit;
    document.getElementById('detailMood').textContent = log.mood + '/10';
    if (log.note) { document.getElementById('detailNote').style.display = 'block'; document.getElementById('detailNoteText').textContent = log.note; }
    else { document.getElementById('detailNote').style.display = 'none'; }
    document.getElementById('dayDetail').style.display = 'block';
}
function closeDayDetail() { document.getElementById('dayDetail').style.display = 'none'; }

// ═══════ CHECKIN ═══════
function openCheckin() {
    if (!userData || !userData.goal) { showToast('Сначала создай цель через бота', 'error'); return; }
    document.getElementById('checkinModal').style.display = 'flex';
    document.getElementById('checkinUnit').textContent = userData.unit;
    document.getElementById('checkinAmount').value = '';
    document.getElementById('checkinNote').value = '';
    selectedMood = 5;
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    document.querySelector('.mood-btn[data-mood="5"]').classList.add('selected');
}
function closeCheckin() { document.getElementById('checkinModal').style.display = 'none'; }
function selectMood(m) {
    selectedMood = m;
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    document.querySelector('.mood-btn[data-mood="' + m + '"]').classList.add('selected');
}
function submitCheckin() {
    const amount = parseFloat(document.getElementById('checkinAmount').value) || 0;
    const note = document.getElementById('checkinNote').value || null;
    if (amount < 0) { showToast('Сумма не может быть отрицательной', 'error'); return; }
    if (!userData.userId) { showToast('Открой через Telegram бота', 'error'); return; }

    fetch(getApiBase() + '/api/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userData.userId, earned: amount, note: note, mood: selectedMood })
    })
    .then(r => r.json())
    .then(d => {
        if (d.status === 'ok') {
            if (userData.goal) { userData.goal.current += amount; }
            userData.totalEarned += amount;
            userData.activeDays++;
            const today = new Date().toISOString().split('T')[0];
            userData.logs[today] = { earned: amount, mood: selectedMood, note: note };
            updateUI();
            renderCalendar();
            closeCheckin();
            showToast('Прогресс записан!', 'success');
        } else {
            showToast('Ошибка: ' + (d.error || 'неизвестно'), 'error');
        }
    })
    .catch(e => { showToast('Ошибка сети', 'error'); });
}

// ═══════ WISH ═══════
function openWish() {
    document.getElementById('wishModal').style.display = 'flex';
    document.getElementById('wishInput').value = '';
}
function closeWish() { document.getElementById('wishModal').style.display = 'none'; }
function submitWish() {
    const text = document.getElementById('wishInput').value.trim();
    if (!text) { showToast('Напиши желание', 'error'); return; }
    if (!userData.userId) { showToast('Открой через Telegram бота', 'error'); return; }

    fetch(getApiBase() + '/api/wish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userData.userId, text: text })
    })
    .then(r => r.json())
    .then(d => {
        if (d.status === 'ok') {
            userData.wish = text;
            updateUI();
            closeWish();
            showToast('Желание загадано!', 'success');
        }
    })
    .catch(e => { showToast('Ошибка сети', 'error'); });
}

// ═══════ CHART ═══════
function renderChart() {
    const canvas = document.getElementById('progressCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const size = 240;
    canvas.width = size * 2;
    canvas.height = size * 2;
    canvas.style.width = size + 'px';
    canvas.style.height = size + 'px';
    ctx.scale(2, 2);

    const cx = size / 2, cy = size / 2, r = 90, lw = 12;
    const pct = (userData && userData.goal && userData.goal.target > 0)
        ? Math.min(userData.goal.current / userData.goal.target, 1) : 0;

    ctx.clearRect(0, 0, size, size);

    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth = lw;
    ctx.lineCap = 'round';
    ctx.stroke();

    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + (Math.PI * 2 * pct);

    if (pct > 0) {
        const grad = ctx.createLinearGradient(0, 0, size, size);
        grad.addColorStop(0, '#6366f1');
        grad.addColorStop(0.5, '#8b5cf6');
        grad.addColorStop(1, '#a78bfa');

        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, endAngle);
        ctx.strokeStyle = grad;
        ctx.lineWidth = lw;
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.shadowColor = 'rgba(99, 102, 241, 0.4)';
        ctx.shadowBlur = 15;
        ctx.beginPath();
        ctx.arc(cx, cy, r, endAngle - 0.05, endAngle);
        ctx.strokeStyle = '#a78bfa';
        ctx.lineWidth = lw;
        ctx.lineCap = 'round';
        ctx.stroke();
        ctx.shadowBlur = 0;
    }

    ctx.fillStyle = '#f0f0f5';
    ctx.font = 'bold 36px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText((pct * 100).toFixed(1) + '%', cx, cy - 8);

    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '13px Inter, sans-serif';
    if (userData && userData.goal) {
        ctx.fillText(userData.goal.current.toLocaleString() + ' / ' + userData.goal.target.toLocaleString() + ' ' + userData.unit, cx, cy + 22);
    } else {
        ctx.fillText('Нет данных', cx, cy + 22);
    }

    const statsEl = document.getElementById('chartStats');
    if (statsEl && userData) {
        const days = userData.activeDays || 0;
        const total = userData.totalEarned || 0;
        const avg = days > 0 ? Math.round(total / days) : 0;
        const streak = userData.streak || 0;

        let deadlineText = '—';
        if (userData.goal && userData.goal.deadline) {
            const dl = new Date(userData.goal.deadline);
            const now = new Date();
            const d = Math.ceil((dl - now) / 86400000);
            deadlineText = d > 0 ? d + ' дн.' : 'Срок вышел';
        }

        statsEl.innerHTML =
            '<div class="chart-stat"><span class="cs-label">Дней в работе</span><span class="cs-value">' + days + '</span></div>' +
            '<div class="chart-stat"><span class="cs-label">Собрано</span><span class="cs-value">' + total.toLocaleString() + ' ' + userData.unit + '</span></div>' +
            '<div class="chart-stat"><span class="cs-label">Среднее в день</span><span class="cs-value">' + avg.toLocaleString() + '</span></div>' +
            '<div class="chart-stat"><span class="cs-label">Текущая серия</span><span class="cs-value">' + streak + ' дн.</span></div>' +
            '<div class="chart-stat"><span class="cs-label">Дедлайн</span><span class="cs-value">' + deadlineText + '</span></div>';
    }
}

// ═══════ REVIEWS ═══════
const allReviews = [
    { name: 'Алексей К.', initials: 'АК', date: '2 дня назад', text: 'Поставил цель заработать на ноутбук. За полтора месяца накопил нужную сумму. Бот каждый день напоминал, и я не мог пропустить ни одного дня.', result: 'Накопил 180 000 руб за 45 дней' },
    { name: 'Мария В.', initials: 'МВ', date: 'неделю назад', text: 'Хотела набрать 10 000 подписчиков в Telegram-канале. Каждый вечер отмечала прогресс, и через два месяца цель была достигнута.', result: '10 000 подписчиков за 58 дней' },
    { name: 'Дмитрий С.', initials: 'ДС', date: '3 дня назад', text: 'Ставил спортивные цели — бегать каждый день. Серия в 30 дней помогла мне похудеть на 8 кг. Теперь бегаю марафоны!', result: 'Серия 45 дней, минус 12 кг' },
    { name: 'Елена М.', initials: 'ЕМ', date: '5 дней назад', text: 'Цель — выучить английский за 3 месяца. Каждый день отмечала часы занятий. Через 80 дней свободно разговаривала с иностранцами.', result: 'Выучила английский за 80 дней' },
    { name: 'Игорь Р.', initials: 'ИР', date: 'вчера', text: 'Накопил на первый взнос за квартиру. Казалось невозможным, но каждый день делал хотя бы маленький шаг.', result: '650 000 руб за 4 месяца' },
    { name: 'Анна Л.', initials: 'АЛ', date: '4 дня назад', text: 'Запустила свой бизнес. Ставила ежедневные цели по продажам, и через 2 месяца вышла на стабильный доход.', result: 'Запустила бизнес за 60 дней' },
    { name: 'Павел Т.', initials: 'ПТ', date: '6 дней назад', text: 'Хотел написать книгу. Ставил цель писать по 1000 слов в день. Через 3 месяца рукопись была готова.', result: 'Написал книгу за 90 дней' },
    { name: 'Ольга Н.', initials: 'ОН', date: '2 дня назад', text: 'Цель — пробежать 10 км без остановки. Начала с 1 км. Через 2 месяца пробежала свои первые 10 км.', result: '10 км за 67 дней' },
    { name: 'Сергей В.', initials: 'СВ', date: 'вчера', text: 'Копил на отпуск мечты. Каждый день откладывал определённую сумму. Через 5 месяцев был на Мальдивах.', result: '350 000 руб за 5 месяцев' },
    { name: 'Наталья К.', initials: 'НК', date: '3 дня назад', text: 'Научилась готовить 50 блюд за месяц. Каждый день отмечала新的рецепт. Теперь кормлю всю семью!', result: '50 блюд за 30 дней' },
    { name: 'Виктор П.', initials: 'ВП', date: 'неделю назад', text: 'Бросил курить с помощью бота. Каждый день отмечал прогресс. Уже 100 дней без сигарет!', result: '100 дней без курения' },
    { name: 'Ирина Д.', initials: 'ИД', date: '5 дней назад', text: 'Набрала 1000 подписчиков в Instagram. Поставила цель — 1 пост в день. За 3 месяца цель достигнута.', result: '1000 подписчиков за 90 дней' },
];
let reviewIndex = 0;
let reviewTimer = null;

function shuffleArray(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

function renderReviewCards(startIdx) {
    const c = document.getElementById('reviewsList');
    if (!c) return;
    c.innerHTML = '';
    const shuffled = shuffleArray(allReviews);
    const show = shuffled.slice(0, 3);
    show.forEach((r, i) => {
        const card = document.createElement('div');
        card.className = 'review-card';
        card.style.animationDelay = (i * 0.15) + 's';
        card.innerHTML = '<div class="review-header"><div class="review-avatar">' + r.initials + '</div><div class="review-info"><div class="review-name">' + r.name + '</div><div class="review-date">' + r.date + '</div></div><span class="review-verified">Проверено</span></div><div class="review-text">' + r.text + '</div><div class="review-result">&#9656; ' + r.result + '</div>';
        c.appendChild(card);
    });
}

function initReviews() {
    renderReviewCards(0);
    reviewTimer = setInterval(() => {
        const c = document.getElementById('reviewsList');
        if (!c) return;
        c.style.opacity = '0';
        c.style.transform = 'translateY(10px)';
        setTimeout(() => {
            renderReviewCards(++reviewIndex);
            c.style.transition = 'all 0.4s ease';
            c.style.opacity = '1';
            c.style.transform = 'translateY(0)';
        }, 300);
    }, 5000);
}

// ═══════ TOAST ═══════
function showToast(msg, type) {
    type = type || 'success';
    const old = document.querySelector('.toast');
    if (old) old.remove();
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    t.textContent = msg;
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 2500);
}
