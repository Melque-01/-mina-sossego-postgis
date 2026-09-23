# ROTEIRO QGIS — Mina do Sossego x MapBiomas (trocar sintético pelo real)

Objetivo: sair do `gerar_base.py` (sintético) para número defensável com dado livre.

## 1. Mina (ponto)
1. QGIS → nova camada ponto WGS84 (4326): lon **-50.0790**, lat **-6.4325** (cava Sequeirinho/Sossego).
2. Ajuste fino: imagem satélite ESRI/Bing + polígono ANM (SIGMINE). Mova o ponto pra dentro da cava e anote a fonte.
3. Salve `mina.geojson`.

## 2. Buffers (o "entorno")
1. Reprojete o ponto para **31982** (UTM 22S SIRGAS2000 — mesmo do banco).
2. `Vetor → Geoprocessamento → Buffer`: **1000m, 5000m, 10000m**, segmentos 32.
3. Salve `buffers.shp` com campo `raio_km`. Justificativa pronta:
   - 1km = impacto direto (cava, pilha, planta);
   - 5km = funcional (vila Sossego, acessos, terceiros);
   - 10km = controle (fundo agropecuário regional).

## 3. MapBiomas (ciclos 2008 / 2015 / 2023)
1. Baixe Coleção MapBiomas Amazônia (ou toolkit QGIS MapBiomas): anos **2008, 2015, 2023**.
   Por quê: 2008 pré-expansão, 2015 operação plena, 2023 recente. Série anual longa = vantagem sobre PRODES p/ tendência.
2. Recorte pelo buffer 10km: `Raster → Extração → Cortar`.
3. Reclassifique: floresta (3,4,5) = 1; mineração (30) / pastagem (15) / outros = classes de perda.
   Use `Semi-automatic Classification` ou `Raster Calculator`.
4. `Raster → Conversão → Poligonizar` só das áreas de perda por ano. Simplifique geometria (tolerância 10m).
5. Calcule `area_ha = $area/10000` e confira: soma por ano ≈ `vw_serie_buffer` depois da importação.

## 4. Importar pra VM (PostGIS)
```bash
# no host, pasta do QGIS (use DB_PASS do .env):
PGPASSWORD="$DB_PASS" shp2pgsql -s 31982 -g geom buffers.shp buffer_entorno_tmp | psql -h localhost -p 15432 -U "$DB_USER" -d "$DB_NAME"
PGPASSWORD="$DB_PASS" shp2pgsql -s 31982 -g geom desmate_2008.shp desmate_tmp | psql ...
# depois:
# INSERT INTO desmate (ano, classe, fonte, geom) SELECT 2008, classe, 'MapBiomas', ST_Multi(geom) FROM desmate_tmp;
# UPDATE desmate SET area_ha = ST_Area(geom)/10000;
```

## 5. Conferência (vira ENTREGA)
```sql
SELECT raio_km, ano, SUM(ha) FROM vw_serie_buffer GROUP BY 1,2 ORDER BY 1,2;
```
Bate com o número do QGIS? Se divergir >2%, cheque SRID e interseção parcial na borda.

## 6. Interpretação (o que diferencia de mapa automático)
- Pastagem cresce ao longo de vicinais no 5km? → vetor agropecuário, não mina.
- Mineração concentrada no 1km e estável após 2015? → impacto direto confinado.
- Escreva 1 parágrafo com esses dois pontos + print do gráfico do dashboard.
