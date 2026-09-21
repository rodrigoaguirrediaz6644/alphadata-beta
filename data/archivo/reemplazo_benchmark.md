# Reemplazo del benchmark — 21-09-2026

Reemplazo **total** de la serie `IPSA_TR`. No es un parche.

| | antes | después |
|---|---|---|
| fuente | ETF proxy `CFMITNIPSA.SN`, descarga automática | MSCI IPSA Gross, descarga manual semanal |
| ruedas | 2,916 | 1,423 |
| desde | 02-01-2015 | 04-01-2021 |
| hasta | 17-09-2026 | 17-09-2026 |
| mayor variación diaria | 12.00% | 9.69% |

La serie anterior queda íntegra en `ipsa_tr_proxy_cfmitnipsa.csv`. No se borró
ni se empalmó con la nueva: empalmar dos series de niveles distintos fue lo que
produjo el salto de 100 a 212,56 en el NAV.

Se pierde la historia anterior al 04-01-2021; la
reconstrucción oficial arranca el 08-07-2021 y no la necesita.

`config/tickers.csv` queda con `estado = manual`, que la excluye de la descarga
automática sin sacarla del universo ni del informe de cobertura.
