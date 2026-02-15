// Premium Booking Form JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth animations and interactions
    const form = document.querySelector('.form-container, #booking-form');
    const inputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="number"], textarea, select');
    const submitButtons = document.querySelectorAll('.premium-submit-row input[type="submit"]');
    
    // Animate form on load
    if (form) {
        form.style.opacity = '0';
        form.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            form.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
            form.style.opacity = '1';
            form.style.transform = 'translateY(0)';
        }, 100);
    }
    
    // Enhanced input interactions
    inputs.forEach(input => {
        // Add floating label effect
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
            
            // Add ripple effect
            const ripple = document.createElement('span');
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(37, 99, 235, 0.3)';
            ripple.style.width = '0';
            ripple.style.height = '0';
            ripple.style.top = '50%';
            ripple.style.left = '50%';
            ripple.style.transform = 'translate(-50%, -50%)';
            ripple.style.pointerEvents = 'none';
            ripple.style.transition = 'all 0.6s ease-out';
            
            this.parentElement.style.position = 'relative';
            this.parentElement.appendChild(ripple);
            
            setTimeout(() => {
                ripple.style.width = '200px';
                ripple.style.height = '200px';
                ripple.style.opacity = '0';
            }, 10);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('focused');
        });
        
        // Add character counter for textareas
        if (input.tagName === 'TEXTAREA') {
            const counter = document.createElement('div');
            counter.className = 'char-counter';
            counter.style.cssText = `
                position: absolute;
                bottom: -20px;
                right: 0;
                font-size: 0.75rem;
                color: #94a3b8;
                font-weight: 500;
                transition: all 0.3s ease;
            `;
            counter.textContent = `${input.value.length} znaków`;
            
            input.parentElement.style.position = 'relative';
            input.parentElement.appendChild(counter);
            
            input.addEventListener('input', function() {
                counter.textContent = `${this.value.length} znaków`;
                if (this.value.length > 200) {
                    counter.style.color = '#f59e0b';
                } else {
                    counter.style.color = '#94a3b8';
                }
            });
        }
    });
    
    // Enhanced button interactions
    submitButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-6px) scale(1.05)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
        
        button.addEventListener('click', function(e) {
            // Add loading state
            this.classList.add('loading');
            
            // Create ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.3);
                left: ${x}px;
                top: ${y}px;
                pointer-events: none;
                transform: scale(0);
                animation: ripple 0.6s ease-out;
            `;
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
                this.classList.remove('loading');
            }, 600);
        });
    });
    
    // Add CSS for ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: scale(2);
                opacity: 0;
            }
        }
        
        .form-row {
            position: relative;
            transition: all 0.3s ease;
        }
        
        .form-row.focused {
            transform: translateX(5px);
        }
        
        .form-row::before {
            content: '';
            position: absolute;
            left: -20px;
            top: 50%;
            width: 4px;
            height: 0;
            background: linear-gradient(135deg, #2563eb, #7c3aed);
            border-radius: 2px;
            transition: all 0.3s ease;
            transform: translateY(-50%);
        }
        
        .form-row.focused::before {
            height: 60%;
        }
    `;
    document.head.appendChild(style);
    
    // Auto-save functionality
    let autoSaveTimer;
    const autoSaveInputs = document.querySelectorAll('input[type="text"], textarea');
    
    autoSaveInputs.forEach(input => {
        input.addEventListener('input', function() {
            clearTimeout(autoSaveTimer);
            autoSaveTimer = setTimeout(() => {
                // Show auto-save indicator
                const indicator = document.createElement('div');
                indicator.textContent = '✅ Auto-zapisano';
                indicator.style.cssText = `
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: linear-gradient(135deg, #10b981, #059669);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 8px;
                    font-weight: 600;
                    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
                    z-index: 9999;
                    animation: slideInRight 0.3s ease-out;
                `;
                document.body.appendChild(indicator);
                
                setTimeout(() => {
                    indicator.style.animation = 'slideOutRight 0.3s ease-out';
                    setTimeout(() => indicator.remove(), 300);
                }, 2000);
            }, 2000);
        });
    });
    
    // Add animations CSS
    const animationStyle = document.createElement('style');
    animationStyle.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(animationStyle);

    // ===== IMPROVED DATE & TIME PICKER =====
    // Zastąp standardowy datetime picker lepszym rozwiązaniem
    const dateTimeInputs = document.querySelectorAll('input.datetime-input, input[name*="start_time"], input[name*="end_time"]');

    console.log('Found datetime inputs:', dateTimeInputs.length);  // Debug

    dateTimeInputs.forEach(input => {
        console.log('Processing input:', input.name, input.type, input.className);  // Debug
        // Sprawdź czy to pole datetime - działa dla pustych i wypełnionych pól
        enhanceDateTimePicker(input);
    });

    function enhanceDateTimePicker(originalInput) {
        const fieldName = originalInput.name;
        const labelText = fieldName.includes('start') ? '📅 Data i czas rozpoczęcia' : '📅 Data i czas zakończenia';

        // Ukryj oryginalny input
        originalInput.style.display = 'none';

        // Parsuj istniejącą wartość lub ustaw domyślną
        let currentDate = new Date();
        let currentHour = 9;  // Domyślna godzina 9:00
        let currentMinute = 0;

        if (originalInput.value && originalInput.value.trim() !== '') {
            const parts = originalInput.value.trim().split(' ');
            if (parts.length >= 2) {
                const dateParts = parts[0].split('/');
                if (dateParts.length === 3) {
                    currentDate = new Date(dateParts[2], dateParts[1] - 1, dateParts[0]);
                }
                const timeParts = parts[1].split(':');
                if (timeParts.length >= 2) {
                    currentHour = parseInt(timeParts[0]);
                    currentMinute = parseInt(timeParts[1]);
                }
            }
        } else {
            // Dla pustych pól: jeśli to end_time, ustaw o godzinę później
            if (originalInput.name.includes('end_time')) {
                currentHour = 10;  // Domyślnie 10:00 dla czasu zakończenia
            }
        }

        // Utwórz nowy kontener
        const container = document.createElement('div');
        container.className = 'enhanced-datetime-picker';
        container.style.cssText = `
            display: flex;
            gap: 1rem;
            align-items: start;
            margin-bottom: 1.5rem;
        `;

        // Kontener na datę
        const dateContainer = document.createElement('div');
        dateContainer.style.cssText = `
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        `;

        const dateLabel = document.createElement('label');
        dateLabel.textContent = '📅 Data';
        dateLabel.style.cssText = `
            color: rgba(226, 232, 240, 0.9);
            font-weight: 600;
            font-size: 0.9rem;
        `;

        const dateInput = document.createElement('input');
        dateInput.type = 'date';
        dateInput.value = currentDate.toISOString().split('T')[0];
        dateInput.style.cssText = `
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: rgba(226, 232, 240, 0.95);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
            cursor: pointer;
        `;

        dateInput.addEventListener('focus', function() {
            this.style.borderColor = 'rgba(37, 99, 235, 0.6)';
            this.style.background = 'rgba(37, 99, 235, 0.1)';
            this.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)';
        });

        dateInput.addEventListener('blur', function() {
            this.style.borderColor = 'rgba(255, 255, 255, 0.15)';
            this.style.background = 'rgba(255, 255, 255, 0.08)';
            this.style.boxShadow = 'none';
        });

        dateContainer.appendChild(dateLabel);
        dateContainer.appendChild(dateInput);

        // Kontener na czas rozpoczęcia
        const timeContainer = document.createElement('div');
        timeContainer.style.cssText = `
            display: flex;
            gap: 0.75rem;
            align-items: end;
        `;

        // Godzina
        const hourContainer = document.createElement('div');
        hourContainer.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        `;

        const hourLabel = document.createElement('label');
        hourLabel.textContent = '🕐 Godzina';
        hourLabel.style.cssText = `
            color: rgba(226, 232, 240, 0.9);
            font-weight: 600;
            font-size: 0.9rem;
        `;

        const hourSelect = document.createElement('select');
        hourSelect.style.cssText = `
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: rgba(226, 232, 240, 0.95);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            cursor: pointer;
            min-width: 80px;
        `;

        for (let h = 0; h < 24; h++) {
            const option = document.createElement('option');
            option.value = h;
            option.textContent = h.toString().padStart(2, '0');
            if (h === currentHour) option.selected = true;
            hourSelect.appendChild(option);
        }

        hourContainer.appendChild(hourLabel);
        hourContainer.appendChild(hourSelect);

        // Minuta
        const minuteContainer = document.createElement('div');
        minuteContainer.style.cssText = `
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        `;

        const minuteLabel = document.createElement('label');
        minuteLabel.textContent = '⏱️ Minuta';
        minuteLabel.style.cssText = `
            color: rgba(226, 232, 240, 0.9);
            font-weight: 600;
            font-size: 0.9rem;
        `;

        const minuteSelect = document.createElement('select');
        minuteSelect.style.cssText = `
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: rgba(226, 232, 240, 0.95);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
            cursor: pointer;
            min-width: 80px;
        `;

        for (let m = 0; m < 60; m += 15) {
            const option = document.createElement('option');
            option.value = m;
            option.textContent = m.toString().padStart(2, '0');
            if (m === currentMinute || (m <= currentMinute && currentMinute < m + 15)) {
                option.selected = true;
            }
            minuteSelect.appendChild(option);
        }

        minuteContainer.appendChild(minuteLabel);
        minuteContainer.appendChild(minuteSelect);

        timeContainer.appendChild(hourContainer);
        timeContainer.appendChild(minuteContainer);

        // Dodaj hover effects dla select
        [hourSelect, minuteSelect].forEach(select => {
            select.addEventListener('focus', function() {
                this.style.borderColor = 'rgba(37, 99, 235, 0.6)';
                this.style.background = 'rgba(37, 99, 235, 0.1)';
                this.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)';
            });

            select.addEventListener('blur', function() {
                this.style.borderColor = 'rgba(255, 255, 255, 0.15)';
                this.style.background = 'rgba(255, 255, 255, 0.08)';
                this.style.boxShadow = 'none';
            });
        });

        // Funkcja aktualizująca ukryty input
        function updateOriginalInput() {
            const date = new Date(dateInput.value);
            const hour = hourSelect.value.padStart(2, '0');
            const minute = minuteSelect.value.padStart(2, '0');

            const day = date.getDate().toString().padStart(2, '0');
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            const year = date.getFullYear();

            originalInput.value = `${day}/${month}/${year} ${hour}:${minute}:00`;
        }

        // Event listenery
        dateInput.addEventListener('change', updateOriginalInput);
        hourSelect.addEventListener('change', updateOriginalInput);
        minuteSelect.addEventListener('change', updateOriginalInput);

        // Złóż wszystko razem
        container.appendChild(dateContainer);
        container.appendChild(timeContainer);

        // Wstaw nowy kontener po oryginalnym input
        originalInput.parentNode.insertBefore(container, originalInput.nextSibling);

        // Ustaw domyślną wartość jeśli pole było puste
        if (!originalInput.value || originalInput.value.trim() === '') {
            updateOriginalInput();
        }
    }
});
