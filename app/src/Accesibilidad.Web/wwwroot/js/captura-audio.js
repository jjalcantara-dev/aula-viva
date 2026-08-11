// Captura del micrófono y envío al servidor por el circuito de Blazor Server (SignalR).
//
// Nota de arquitectura: los fragmentos viajan por el mismo websocket que ya usa Blazor
// Server, vía JSInterop. Es el camino real que recorrería el audio en producción, así que
// la latencia medida es representativa. Un hub de SignalR dedicado será necesario cuando
// haya que difundir a varios receptores; para medir el circuito no aporta nada.
//
// MEDICIÓN DE LATENCIA. El reloj del navegador y el del servidor no están sincronizados,
// así que restar una marca de tiempo del cliente a una del servidor daría un número
// inventado. Aquí se mide el viaje COMPLETO de ida y vuelta con un único reloj, el del
// navegador: se anota cuándo sale el fragmento y cuándo el subtítulo correspondiente ya
// está en pantalla.
//
// La secuencia la asigna el cliente, no el servidor, precisamente para poder emparejar
// cada subtítulo con el fragmento que lo originó.

let contexto = null;
let flujo = null;
let nodo = null;
let origen = null;

let secuencia = 0;
/** secuencia -> instante de envío (performance.now) */
const pendientes = new Map();

/**
 * @param {object} refDotnet  referencia al componente Blazor
 * @param {number} frecuencia frecuencia de muestreo deseada (16000 para Whisper)
 * @param {number} msPorFragmento tamaño del bloque en milisegundos
 * @param {boolean} preprocesado activar supresión de ruido/eco/ganancia del navegador
 * @returns {Promise<number>} frecuencia real concedida por el navegador
 */
export async function iniciar(refDotnet, frecuencia, msPorFragmento, preprocesado, gananciaAuto) {
    secuencia = 0;
    pendientes.clear();

    // El preprocesado del navegador (WebRTC) NO es neutro: está afinado para
    // inteligibilidad en llamadas, no para reconocimiento.
    //
    // El control automático de ganancia va SEPARADO y desactivado por defecto porque
    // sabotea la segmentación por silencios: al callar el hablante, el AGC sube la
    // ganancia y amplifica el ruido de fondo, de modo que la energía nunca baja y las
    // pausas dejan de detectarse. Medido en uso real: con AGC activo, casi todos los
    // segmentos se cerraban por agotar el tope en lugar de por pausa.
    flujo = await navigator.mediaDevices.getUserMedia({
        audio: {
            channelCount: 1,
            echoCancellation: preprocesado,
            noiseSuppression: preprocesado,
            autoGainControl: gananciaAuto,
        },
    });

    // El navegador puede no conceder la frecuencia pedida; se devuelve la real para
    // que el servidor sepa a qué frecuencia está el PCM que recibe.
    contexto = new AudioContext({ sampleRate: frecuencia });
    await contexto.audioWorklet.addModule('js/pcm-worklet.js');

    const muestrasPorBloque = Math.round((contexto.sampleRate * msPorFragmento) / 1000);
    nodo = new AudioWorkletNode(contexto, 'procesador-pcm', {
        processorOptions: { muestrasPorBloque },
    });

    nodo.port.onmessage = (e) => {
        const seq = secuencia++;
        pendientes.set(seq, performance.now());
        refDotnet.invokeMethodAsync('RecibirFragmento', seq, new Uint8Array(e.data));
    };

    origen = contexto.createMediaStreamSource(flujo);
    origen.connect(nodo);

    return contexto.sampleRate;
}

/**
 * Cierra la medida de un fragmento. Lo llama el componente cuando el subtítulo ya se ha
 * renderizado, así que el número incluye red, servidor, motor y pintado.
 *
 * @param {number} seq secuencia del fragmento que originó el subtítulo
 * @returns {number} milisegundos de ida y vuelta, o -1 si no se encontró
 */
export function marcarRecibido(seq) {
    const t0 = pendientes.get(seq);
    if (t0 === undefined) return -1;

    // Con ventanas largas, un subtítulo consume varios fragmentos y solo se cierra el
    // primero. Los anteriores ya no se van a cerrar nunca: se descartan para que el mapa
    // no crezca sin límite durante una clase entera.
    for (const clave of pendientes.keys()) {
        if (clave <= seq) pendientes.delete(clave);
    }
    return performance.now() - t0;
}

export async function detener() {
    if (origen) { origen.disconnect(); origen = null; }
    if (nodo) { nodo.port.onmessage = null; nodo.disconnect(); nodo = null; }
    if (flujo) { flujo.getTracks().forEach((t) => t.stop()); flujo = null; }
    if (contexto) { await contexto.close(); contexto = null; }
    pendientes.clear();
}
