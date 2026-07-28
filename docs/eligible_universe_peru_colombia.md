# Inventario de acciones elegibles — Perú y Colombia

Estado inicial al 28 de julio de 2026. Este inventario prepara la investigación y los backtests; no activa descargas productivas ni incorpora todavía estrategias al informe.

## Principios

1. La pertenencia a un índice es condición de observación, no elegibilidad automática.
2. Cada valor debe superar cobertura histórica, negociación, liquidez monetaria y calidad del retorno total.
3. Acciones ordinarias y preferenciales del mismo emisor se tratan como una sola exposición económica.
4. No se rellenan precios ni volúmenes faltantes para simular liquidez.
5. Los símbolos de proveedor son candidatos hasta que una prueba automática confirme su cobertura.

## Referencias oficiales

- Perú: MSCI nuam Peru Select Capped 15%, publicado por BVL. La BVL informó 18 compañías representativas en marzo de 2026.
- Colombia: MSCI COLCAP. MSCI reportó 22 valores al 30 de junio de 2026 y publica sus diez mayores posiciones.
- Colombia operable: iShares MSCI COLCAP se utiliza sólo como contraste de composición y posible benchmark, no como acción elegible.

## Estados

- `candidato_liquido`: existe evidencia inicial de cotización líquida local o internacional.
- `candidato`: pasa a prueba automática de datos y liquidez.
- `condicionado`: requiere confirmación de negociación, clase, historia o proveedor.
- `reserva`: sólo entra si supera filtros estrictos.
- `benchmark_operable`: vehículo de comparación, no acción seleccionable.

## Filtros propuestos para la siguiente etapa

Los umbrales definitivos se fijarán después de medir la distribución real de ambos mercados:

- al menos 3 años de precios diarios ajustados, idealmente 5;
- cobertura mínima de 95% de ruedas en la ventana de señal;
- porcentaje máximo de días sin transacción;
- mediana de valor negociado diario y percentil de liquidez por país;
- precio no obsoleto al rebalanceo;
- historial de dividendos y splits conciliado;
- máximo una clase por emisor económico;
- trazabilidad de altas y bajas del índice para evitar sesgo de supervivencia.

## Fuentes

- https://www.bvl.com.pe/en/market/msci-nuam-peru-select-capped-15-index
- https://www.bvl.com.pe/bvlupdate/indice-msci-peru-select-dame-luz-030326
- https://www.msci.com/indexes/index/737809/msci-colcap-index
- https://www.bvc.com.co/msci-colcap
- https://www.blackrock.com/co/productos/251708/ishares-fondo-burstil-ishares-colcap-fund

## Limitación conocida

Las listas completas actuales no se exponen de forma uniforme en páginas estáticas. Los registros marcados `candidato_por_verificar` son un universo de investigación, no una afirmación de pertenencia vigente. La siguiente tarea debe descargar o reconstruir la composición oficial por fecha y validar cada símbolo antes de habilitarlo.
