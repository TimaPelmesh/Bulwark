document.addEventListener('DOMContentLoaded', function() {
    // Плавная прокрутка для навигации
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 80,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Анимация для карточек с функциями
    const featureCards = document.querySelectorAll('.feature-card');
    
    function checkVisibility() {
        featureCards.forEach(card => {
            const rect = card.getBoundingClientRect();
            const isVisible = rect.top <= window.innerHeight * 0.75 && rect.bottom >= 0;
            
            if (isVisible) {
                card.classList.add('animate');
            }
        });
    }
    
    // Добавляем класс .animate
    document.addEventListener('scroll', checkVisibility);
    window.addEventListener('resize', checkVisibility);
    checkVisibility();
    
    // Счетчик обратного отсчета до релиза следующей версии
    const releaseDate = new Date();
    releaseDate.setDate(releaseDate.getDate() + 30); // Следующий релиз через 30 дней
    
    function updateCountdown() {
        const now = new Date();
        const timeDiff = releaseDate - now;
        
        if (timeDiff > 0) {
            const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
            
            const countdownElement = document.getElementById('countdown');
            if (countdownElement) {
                countdownElement.textContent = `${days}д ${hours}ч ${minutes}м`;
            }
        }
    }
    
    // Обновляем счетчик каждую минуту
    updateCountdown();
    setInterval(updateCountdown, 60000);
    
    // Обработка кликов по ссылкам скачивания
    const downloadButtons = document.querySelectorAll('.download-link');
    
    downloadButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Если ссылка — скачивание файла
            if (this.hasAttribute('download')) {
                // Здесь можно отслеживать статистику скачиваний
                console.log('Файл скачивается...');
            }
            // Для внешних ссылок (GitHub) позволяем браузеру обработать клик стандартно
        });
    });

    // Создаем директорию для загрузок, если это в локальной среде разработки
    async function createDownloadDirIfNeeded() {
        if (window.location.protocol === 'file:') {
            console.log('Локальное окружение. Создание директорий не требуется.');
        }
    }
    
    createDownloadDirIfNeeded();
    
    // Добавляем дату последнего обновления
    const lastUpdatedElement = document.getElementById('last-updated');
    if (lastUpdatedElement) {
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        lastUpdatedElement.textContent = new Date().toLocaleDateString('ru-RU', options);
    }

    // Анимация для предпросмотра приложения (заглушка)
    const previewElement = document.getElementById('preview-placeholder');
    if (previewElement) {
        function simulateScreenUpdates() {
            // Случайно меняем фоновый цвет для имитации активности на экране
            const hue = Math.floor(Math.random() * 360);
            previewElement.style.backgroundColor = `hsla(${hue}, 50%, 30%, 0.2)`;
        }
        
        setInterval(simulateScreenUpdates, 2000);
    }
}); 