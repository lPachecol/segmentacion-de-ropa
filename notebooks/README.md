# Experimentos de segmentación

| Notebook | Qué muestra |
| --- | --- |
| [Exploración de máscaras](exploracion-mascaras.ipynb) | Inspección de pares imagen/máscara, lectura del diccionario de etiquetas y preparación de datos |
| [DeepLabV3+](deeplabv3plus.ipynb) | Experimento inicial con PyTorch, entrenamiento y evaluación |
| [U-Net++ a 384 px](unetplusplus-384.ipynb) | Preparación de las cinco clases, aumentos de entrenamiento, normalización ImageNet, entrenamiento y pruebas de inferencia |

Los notebooks conservan el código de los experimentos y se distribuyen con las salidas borradas. Algunos bloques requieren adaptar rutas, conseguir los pares de imágenes y máscaras y reconstruir los CSV intermedios. `labels.csv` contiene el diccionario de etiquetas de origen. El notebook U-Net++ guarda un archivo terminado en `body1.pth`, mientras que el backend presentado apunta a `body.pth`. Los archivos locales tienen hashes diferentes y la carpeta de entrega no documenta la equivalencia de sus resultados. La app usa los pesos configurados en el [README principal](../README.md).

El notebook de U-Net++ emplea argumentos de aumentos de Albumentations 1.x. Usa un entorno de experimentación separado o adapta esas llamadas antes de ejecutarlas con 2.x. El backend tiene sus propias dependencias de inferencia.
