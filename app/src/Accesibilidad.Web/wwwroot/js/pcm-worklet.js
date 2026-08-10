// Convierte el audio del micrófono a PCM 16 bits y lo agrupa en bloques de duración fija.
//
// Se ejecuta en el hilo de audio (AudioWorklet), no en el principal: si esta conversión
// se hiciera en el hilo de UI, el propio renderizado de los subtítulos introduciría
// jitter en la medida de latencia, que es justo lo que queremos medir sin contaminar.
class ProcesadorPcm extends AudioWorkletProcessor {
    constructor(opciones) {
        super();
        this.muestrasPorBloque = opciones.processorOptions.muestrasPorBloque;
        this.acumulador = new Float32Array(this.muestrasPorBloque);
        this.escritas = 0;
    }

    process(entradas) {
        const canal = entradas[0] && entradas[0][0];
        if (!canal) return true;

        for (let i = 0; i < canal.length; i++) {
            this.acumulador[this.escritas++] = canal[i];

            if (this.escritas === this.muestrasPorBloque) {
                const pcm = new Int16Array(this.muestrasPorBloque);
                for (let j = 0; j < this.muestrasPorBloque; j++) {
                    // Recorte antes de escalar: sin esto, un pico > 1.0 da la vuelta
                    // y se convierte en un chasquido.
                    const m = Math.max(-1, Math.min(1, this.acumulador[j]));
                    pcm[j] = m < 0 ? m * 0x8000 : m * 0x7fff;
                }
                // Transferible: se cede el buffer en vez de copiarlo.
                this.port.postMessage(pcm.buffer, [pcm.buffer]);
                this.escritas = 0;
            }
        }
        return true;
    }
}

registerProcessor('procesador-pcm', ProcesadorPcm);
