# Notebooks — solo análisis exploratorio

## La regla

> Los notebooks **consumen** `results/`. Nunca los producen.
> **Nada que aparezca en la memoria sale de un notebook.**

Las cifras, tablas y figuras de la memoria se generan con los scripts de
`research/eval/report/`, que dejan trazabilidad de configuración, semilla y commit.

## Por qué

Un notebook tiene estado oculto y permite ejecución fuera de orden: una celda puede
estar usando una variable redefinida veinte celdas más abajo. Eso hace que un resultado
sea irreproducible sin que se note, y produce diffs ilegibles en git.

El escenario que esta regla evita: llegar a la recta final, tener una tabla en la
memoria y no poder decir de qué ejecución salió ni regenerarla.

## Para qué sí sirven

- Escuchar los clips donde el modelo falla
- Alineamientos palabra a palabra entre referencia e hipótesis
- Tantear hipótesis sobre los errores (terminología, nombres propios, numerales)
- Explorar antes de decidir qué merece convertirse en script

## Higiene

Limpiar las salidas antes de commitear (`Kernel > Restart & Clear Output`). Lo que
importa del notebook es el código, no las salidas pegadas.
