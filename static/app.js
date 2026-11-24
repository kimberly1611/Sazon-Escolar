
(() => {
    'use strict';

    // CONFIGURACIÓN

    const storageKey = 'sazon_escolar_lectura_voz';
    const toggle = document.getElementById('voiceToggle');

    let voiceEnabled = true;
    let voices = [];
    let lastElement = null;
    let lastMessageTime = 0;
    let pointerRecentlyUsed = false;

    try {
        voiceEnabled = localStorage.getItem(storageKey) !== 'off';
    } catch (error) {
        voiceEnabled = true;
    }

    const speechAvailable =
        'speechSynthesis' in window &&
        'SpeechSynthesisUtterance' in window;

    // VOCES DISPONIBLES

    function loadVoices() {
        if (speechAvailable) {
            voices = window.speechSynthesis.getVoices();
        }
    }

    if (speechAvailable) {
        loadVoices();
        window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    }

    // FUNCIONES DE VOZ

    function clean(text) {
        return String(text || '').replace(/\s+/g, ' ').trim();
    }

    function speak(message) {
        const text = clean(message);

        if (!voiceEnabled || !speechAvailable || !text) return;

        // Detener cualquier lectura anterior.
        window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(text);

        utterance.lang = 'es-MX';
        utterance.rate = 1;
        utterance.pitch = 1;

        const spanishVoice =
            voices.find(voice => voice.lang.toLowerCase() === 'es-mx') ||
            voices.find(voice => voice.lang.toLowerCase().startsWith('es'));

        if (spanishVoice) {
            utterance.voice = spanishVoice;
        }

        window.speechSynthesis.speak(utterance);
        lastMessageTime = Date.now();
    }

    // IDENTIFICAR EL TEXTO DE UN ELEMENTO

    function labelFor(element) {
        if (!element) return '';

        const explicit =
            element.dataset.speech ||
            element.getAttribute('aria-label') ||
            element.getAttribute('title');

        if (explicit) return clean(explicit);

        if (element.labels && element.labels.length) {
            const labels = Array.from(element.labels)
                .map(label => label.innerText)
                .join(' ');

            if (labels) return clean(labels);
        }

        const labelledBy = element.getAttribute('aria-labelledby');

        if (labelledBy) {
            const text = labelledBy
                .split(' ')
                .map(id => document.getElementById(id)?.innerText || '')
                .join(' ');

            if (text) return clean(text);
        }

        const parentLabel = element.closest('label');

        if (parentLabel) return clean(parentLabel.innerText);

        return clean(
            element.innerText ||
            element.value ||
            element.placeholder ||
            element.name ||
            ''
        );
    }

    // DESCRIPCIÓN DE BOTONES

    function describeButton(button) {
        const label = labelFor(button);

        const customDescription =
            button.dataset.description ||
            button.dataset.say;

        if (customDescription) return clean(customDescription);

        const form = button.closest('form');

        const action = form
            ? (form.getAttribute('action') || location.pathname)
            : '';

        if (action.includes('/pedido/crear')) {
            return 'Enviar pedido. Este botón sirve para enviar los productos seleccionados a cocina.';
        }

        if (action.includes('/cancelar')) {
            return 'Cancelar pedido. Este botón sirve para cancelar el pedido seleccionado.';
        }

        if (action.includes('/estado')) {
            return 'Actualizar estado. Este botón sirve para cambiar el estado del pedido.';
        }

        if (
            action.includes('/producto/guardar') ||
            action.includes('/producto/nuevo')
        ) {
            return 'Guardar producto. Este botón sirve para guardar un producto en el menú.';
        }

        if (
            action.includes('/producto/') &&
            action.includes('/eliminar')
        ) {
            return 'Eliminar producto. Este botón sirve para quitar un producto del menú.';
        }

        if (action.includes('/usuario/') && action.includes('/rol')) {
            return 'Cambiar rol. Este botón sirve para modificar el tipo de cuenta del usuario.';
        }

        if (action.includes('/iniciar-sesion')) {
            return 'Iniciar sesión. Este botón sirve para entrar a tu cuenta.';
        }

        if (action.includes('/registro')) {
            return 'Registrarse. Este botón sirve para crear una cuenta nueva.';
        }

        const text = label.toLowerCase();

        if (text.includes('iniciar sesión') || text.includes('entrar')) {
            return `${label}. Este botón sirve para acceder a tu cuenta.`;
        }

        if (text.includes('registr')) {
            return `${label}. Este botón sirve para crear una cuenta.`;
        }

        if (text.includes('eliminar') || text.includes('borrar')) {
            return `${label}. Este botón sirve para eliminar el elemento seleccionado.`;
        }

        if (text.includes('cancelar')) {
            return `${label}. Este botón sirve para cancelar la acción o pedido seleccionado.`;
        }

        if (text.includes('guardar')) {
            return `${label}. Este botón sirve para guardar los cambios.`;
        }

        if (text.includes('editar')) {
            return `${label}. Este botón sirve para modificar la información.`;
        }

        if (text.includes('agregar') || text.includes('añadir')) {
            return `${label}. Este botón sirve para agregar un nuevo elemento.`;
        }

        if (text.includes('cerrar sesión') || text.includes('salir')) {
            return `${label}. Este botón sirve para cerrar tu sesión.`;
        }

        if (text.includes('pedido')) {
            return `${label}. Este botón permite realizar o consultar una acción relacionada con los pedidos.`;
        }

        return label ? `Botón ${label}.` : 'Botón de acción.';
    }

    // DESCRIPCIÓN DE CAMPOS

    function describeField(field) {
        const label =
            field.labels?.[0]?.innerText ||
            field.getAttribute('aria-label') ||
            field.name ||
            'Campo';

        if (field.tagName === 'SELECT') {
            const selected = field.selectedOptions[0];

            return `${clean(label)}. Selector de opciones. Opción actual: ${
                selected ? clean(selected.textContent) : 'Ninguna seleccionada'
            }.`;
        }

        if (field.type === 'checkbox') {
            return `${label}. Casilla de selección. Puedes marcarla o desmarcarla.`;
        }

        if (field.type === 'radio') {
            return `${label}. Opción seleccionable.`;
        }

        if (field.type === 'password') {
            return `${label}. Campo para escribir tu contraseña.`;
        }

        if (field.type === 'email') {
            return `${label}. Campo para escribir tu correo electrónico.`;
        }

        if (field.tagName === 'TEXTAREA') {
            return `${label}. Campo para escribir un mensaje o descripción.`;
        }

        if (field.type === 'number') {
            return `${label}. Campo para escribir una cantidad numérica.`;
        }

        return `${label}. Campo de escritura.`;
    }

    // DESCRIPCIÓN DE PRODUCTOS

    function describeProduct(card) {
        if (card.dataset.speech) {
            return clean(card.dataset.speech);
        }

        const title = card.querySelector(
            'h1, h2, h3, h4, .product-name, .producto-nombre, .card-title'
        )?.innerText || '';

        const price = card.querySelector(
            '.price, .precio, [class*="price"], [class*="precio"]'
        )?.innerText || '';

        const description = card.querySelector(
            '.description, .descripcion, [class*="description"], [class*="descripcion"]'
        )?.innerText || '';

        const parts = [title, price, description].filter(Boolean);

        return parts.length
            ? parts.join('. ')
            : clean(card.innerText).slice(0, 250);
    }

    // SELECTOR PERSONALIZADO PARA ESTADOS

    function createStatusSelectors() {
        const statusSelects = document.querySelectorAll(
            '.ticket-foot select[name="status"]'
        );

        statusSelects.forEach(select => {
            if (select.dataset.customized === 'true') return;

            select.dataset.customized = 'true';
            select.dataset.voiceCustomSelect = 'true';

            const wrapper = document.createElement('div');
            wrapper.className = 'voice-select-wrapper';

            const trigger = document.createElement('button');
            trigger.type = 'button';
            trigger.className = 'voice-select-trigger';
            trigger.setAttribute('aria-haspopup', 'listbox');
            trigger.setAttribute('aria-expanded', 'false');

            const menu = document.createElement('div');
            menu.className = 'voice-select-menu';
            menu.setAttribute('role', 'listbox');
            menu.setAttribute('aria-label', 'Estados disponibles del pedido');
            menu.hidden = true;

            const selectedOption = select.selectedOptions[0];

            trigger.textContent = selectedOption
                ? clean(selectedOption.textContent)
                : 'Seleccionar estado';

            trigger.setAttribute(
                'aria-label',
                `Estado actual: ${trigger.textContent}. Abrir opciones`
            );

            select.parentNode.insertBefore(wrapper, select);
            wrapper.appendChild(select);
            wrapper.appendChild(trigger);
            wrapper.appendChild(menu);

            select.classList.add('voice-native-select');

            function closeMenu() {
                menu.hidden = true;
                trigger.setAttribute('aria-expanded', 'false');
            }

            function openMenu() {
                document.querySelectorAll('.voice-select-menu').forEach(otherMenu => {
                    otherMenu.hidden = true;
                });

                document.querySelectorAll('.voice-select-trigger').forEach(otherTrigger => {
                    otherTrigger.setAttribute('aria-expanded', 'false');
                });

                menu.hidden = false;
                trigger.setAttribute('aria-expanded', 'true');

                const selectedButton = menu.querySelector('[aria-selected="true"]');
                const firstButton = menu.querySelector('button');

                (selectedButton || firstButton)?.focus();
            }

            Array.from(select.options).forEach(option => {
                const optionButton = document.createElement('button');

                optionButton.type = 'button';
                optionButton.className = 'voice-select-option';
                optionButton.textContent = clean(option.textContent);
                optionButton.dataset.voiceOption = 'true';
                optionButton.setAttribute('role', 'option');
                optionButton.setAttribute(
                    'aria-selected',
                    String(option.selected)
                );

                optionButton.addEventListener('click', () => {
                    select.value = option.value;

                    Array.from(menu.children).forEach(button => {
                        button.setAttribute('aria-selected', 'false');
                    });

                    optionButton.setAttribute('aria-selected', 'true');

                    trigger.textContent = clean(option.textContent);
                    trigger.setAttribute(
                        'aria-label',
                        `Estado actual: ${trigger.textContent}. Abrir opciones`
                    );

                    closeMenu();

                    select.dispatchEvent(new Event('change', {
                        bubbles: true
                    }));

                    trigger.focus();
                });

                optionButton.addEventListener('keydown', event => {
                    const buttons = Array.from(menu.querySelectorAll('button'));
                    const index = buttons.indexOf(optionButton);

                    if (event.key === 'ArrowDown') {
                        event.preventDefault();
                        buttons[(index + 1) % buttons.length]?.focus();
                    }

                    if (event.key === 'ArrowUp') {
                        event.preventDefault();
                        buttons[(index - 1 + buttons.length) % buttons.length]?.focus();
                    }

                    if (event.key === 'Escape') {
                        closeMenu();
                        trigger.focus();
                    }
                });

                menu.appendChild(optionButton);
            });

            trigger.addEventListener('click', () => {
                if (menu.hidden) {
                    openMenu();
                } else {
                    closeMenu();
                }
            });

            trigger.addEventListener('keydown', event => {
                if (
                    event.key === 'ArrowDown' ||
                    event.key === 'Enter' ||
                    event.key === ' '
                ) {
                    event.preventDefault();
                    openMenu();
                }

                if (event.key === 'Escape') {
                    closeMenu();
                }
            });

            select.addEventListener('change', () => {
                const current = select.selectedOptions[0];

                if (!current) return;

                trigger.textContent = clean(current.textContent);
                trigger.setAttribute(
                    'aria-label',
                    `Estado actual: ${trigger.textContent}. Abrir opciones`
                );

                Array.from(menu.children).forEach(button => {
                    button.setAttribute(
                        'aria-selected',
                        String(button.textContent === trigger.textContent)
                    );
                });
            });
        });
    }

    createStatusSelectors();

    // IDENTIFICAR EL ELEMENTO SEÑALADO

    function getElementToRead(target) {
        if (!(target instanceof Element)) return null;

        // Las opciones de estado deben leerse solamente por su nombre.
        const statusOption = target.closest('[data-voice-option]');

        if (statusOption) {
            return {
                element: statusOption,
                message: clean(statusOption.textContent)
            };
        }

        const statusTrigger = target.closest('.voice-select-trigger');

        if (statusTrigger) {
            return {
                element: statusTrigger,
                message: `Selector de estado. Estado actual: ${clean(statusTrigger.textContent)}. Presiona para ver las opciones disponibles.`
            };
        }

        const control = target.closest(
            'button, a, input, select, textarea, [role="button"]'
        );

        if (control && control !== toggle && !control.classList.contains('voice-native-select')) {
            return {
                element: control,
                message: control.matches('input, select, textarea')
                    ? describeField(control)
                    : describeButton(control)
            };
        }

        const product = target.closest(
            '[data-speak-card], [data-product], [data-product-card], .product-card, .producto-card, .product, .producto, .menu-card, .food-card'
        );

        if (product) {
            return {
                element: product,
                message: describeProduct(product)
            };
        }

        return null;
    }

    // ANUNCIAR UN ELEMENTO

    function announceElement(target) {
        const result = getElementToRead(target);

        if (!result || !result.message) return;
        if (result.element === lastElement) return;

        lastElement = result.element;
        speak(result.message);
    }

    // LECTURA AL PASAR EL MOUSE

    document.addEventListener('pointerover', event => {
        if (event.pointerType === 'touch') return;

        pointerRecentlyUsed = true;
        announceElement(event.target);
    });

    document.addEventListener('pointerout', event => {
        const result = getElementToRead(event.target);

        if (
            result &&
            event.relatedTarget &&
            result.element.contains(event.relatedTarget)
        ) {
            return;
        }

        lastElement = null;
    });

    // NAVEGACIÓN CON TECLADO
    document.addEventListener('keydown', event => {
        if (event.key === 'Tab' || event.key.startsWith('Arrow')) {
            pointerRecentlyUsed = false;
        }
    });

    document.addEventListener('focusin', event => {
        if (pointerRecentlyUsed) {
            pointerRecentlyUsed = false;
            return;
        }

        announceElement(event.target);
    });

    // LECTURA AL HACER CLIC

    document.addEventListener('click', event => {
        const result = getElementToRead(event.target);

        if (!result) return;

        const recentlyRead =
            result.element === lastElement &&
            Date.now() - lastMessageTime < 1500;

        if (!recentlyRead) {
            lastElement = result.element;
            speak(result.message);
        }
    }, true);

    // LECTURA DE LOS SELECTORES NORMALES

    const statusExplanations = {
        recibido: 'El pedido fue recibido y está pendiente de preparación.',
        pendiente: 'El pedido fue recibido y está pendiente de preparación.',
        preparando: 'Cocina está preparando el pedido.',
        listo: 'El pedido está listo para recoger.',
        entregado: 'El pedido ya fue entregado.',
        cancelado: 'El pedido fue cancelado.'
    };

    document.addEventListener('change', event => {
        const field = event.target;

        if (!(field instanceof HTMLSelectElement)) return;

        // El selector visual de estados no debe leer explicaciones largas.
        if (field.dataset.voiceCustomSelect === 'true') return;

        const option = field.selectedOptions[0];
        if (!option) return;

        const selected = clean(option.textContent);

        const label =
            field.labels?.[0]?.innerText ||
            field.getAttribute('aria-label') ||
            'Selector de opciones';

        const explanation =
            statusExplanations[selected.toLowerCase()] ||
            'Esta es la opción que has seleccionado.';

        lastElement = field;

        speak(`${clean(label)}. Seleccionaste ${selected}. ${explanation}`);
    });

    // ACTIVAR Y DESACTIVAR LA VOZ
    function updateToggle() {
        if (!toggle) return;

        toggle.setAttribute('aria-pressed', String(voiceEnabled));

        toggle.setAttribute(
            'aria-label',
            voiceEnabled
                ? 'Desactivar lectura de voz'
                : 'Activar lectura de voz'
        );

        const span = toggle.querySelector('span');

        if (span) {
            span.textContent = voiceEnabled
                ? 'Desactivar lectura de voz'
                : 'Activar lectura de voz';
        }

        toggle.classList.toggle('active', voiceEnabled);
    }

    if (toggle) {
        toggle.addEventListener('click', () => {
            voiceEnabled = !voiceEnabled;

            try {
                localStorage.setItem(storageKey, voiceEnabled ? 'on' : 'off');
            } catch (error) {
                console.warn(error);
            }

            updateToggle();

            if (!voiceEnabled) {
                window.speechSynthesis.cancel();
                lastElement = null;
                return;
            }

            speak(
                'Lectura de voz activada. Pasa el mouse por los botones y productos para escuchar su descripción.'
            );
        });
    }

    updateToggle();

    // CERRAR SELECTORES AL HACER CLIC FUERA

    document.addEventListener('click', event => {
        if (event.target.closest('.voice-select-wrapper')) return;

        document.querySelectorAll('.voice-select-menu').forEach(menu => {
            menu.hidden = true;
        });

        document.querySelectorAll('.voice-select-trigger').forEach(trigger => {
            trigger.setAttribute('aria-expanded', 'false');
        });
    });

    // CONFIRMACIONES

    document.querySelectorAll('[data-confirm]').forEach(button => {
        button.addEventListener('click', event => {
            const confirmation = window.confirm(button.dataset.confirm);

            if (!confirmation) {
                event.preventDefault();
            }
        });
    });

    // CONTADOR DE PRODUCTOS SELECCIONADOS

    const orderForm = document.getElementById('orderForm');
    const count = document.getElementById('selectionCount');

    if (orderForm && count) {
        const boxes = Array.from(
            orderForm.querySelectorAll('input[name="product_id"]')
        );

        const updateCount = () => {
            const selected = boxes.filter(box => box.checked).length;

            count.textContent = `${selected} ${
                selected === 1
                    ? 'producto seleccionado'
                    : 'productos seleccionados'
            }`;
        };

        boxes.forEach(box => {
            box.addEventListener('change', updateCount);
        });

        orderForm.addEventListener('submit', event => {
            const hasProducts = boxes.some(box => box.checked);

            if (!hasProducts) {
                event.preventDefault();
                alert('Selecciona al menos un producto para enviar tu pedido.');
            }
        });

        updateCount();
    }

    console.info('Sazón Escolar: lectura por interacción activada.');
// LECTURA DE LAS OPCIONES DE ESTADO AL PASAR EL MOUSE

document.addEventListener('pointerover', function (event) {
    const opcion = event.target.closest(
        '[data-voice-option="true"], .voice-select-option'
    );

    if (!opcion) return;

    // Evita repetir la lectura mientras el mouse sigue sobre la opción.
    if (lastElement === opcion) return;

    lastElement = opcion;

    if (!voiceEnabled || !('speechSynthesis' in window)) return;

    const nombre = opcion.textContent.trim();

    if (!nombre) return;

    // Detiene cualquier lectura anterior.
    window.speechSynthesis.cancel();

    const mensaje = new SpeechSynthesisUtterance(nombre);
    mensaje.lang = 'es-MX';
    mensaje.rate = 1;

    window.speechSynthesis.speak(mensaje);

}, true);
})();