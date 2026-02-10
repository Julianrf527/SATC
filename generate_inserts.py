import pandas as pd
from collections import defaultdict

# Function to convert UPPER CASE to Title Case
def to_title_case(text):
    """Convert text to proper title case, handling Spanish characters"""
    if not text or pd.isna(text):
        return text
    
    text = str(text).strip()
    
    # Split by spaces and capitalize each word
    words = text.split()
    title_words = []
    
    for word in words:
        # Handle special cases
        if word.upper() in ['DE', 'DEL', 'LA', 'LAS', 'LOS', 'EL']:
            title_words.append(word.lower())
        else:
            # Capitalize first letter, rest lowercase
            title_words.append(word.capitalize())
    
    # Join back, but capitalize first word if it's an article
    result = ' '.join(title_words)
    # Ensure first letter is always capitalized
    if result:
        result = result[0].upper() + result[1:]
    
    return result

# Read Excel file and extract data
print("📖 Leyendo archivo VEREDAS CORPOCHIVOR.xlsx...")
df = pd.read_excel('VEREDAS CORPOCHIVOR.xlsx', header=None)

# Display first few rows to understand structure
print(f"📊 Primeras filas del archivo:")
print(df.head(10))
print(f"\n📊 Forma del DataFrame: {df.shape}")

# Find the row with NOMB_MPIO and NOMBRE_VER
header_row = None
mpio_col = None
vereda_col = None

for idx, row in df.iterrows():
    for col_idx, value in enumerate(row):
        if pd.notna(value):
            value_str = str(value).strip().upper()
            if 'NOMB_MPIO' in value_str:
                header_row = idx
                mpio_col = col_idx
            if 'NOMBRE_VER' in value_str:
                vereda_col = col_idx
    
    if header_row is not None and mpio_col is not None and vereda_col is not None:
        break

print(f"\n🔍 Fila de encabezados: {header_row}")
print(f"🔍 Columna municipios: {mpio_col}")
print(f"🔍 Columna veredas: {vereda_col}")

if header_row is None or mpio_col is None or vereda_col is None:
    print("❌ No se encontraron las columnas NOMB_MPIO y NOMBRE_VER")
    exit(1)

municipios = set()
veredas_data = []

# Process each row after the header
for idx in range(header_row + 1, len(df)):
    row = df.iloc[idx]
    
    if pd.isna(row[mpio_col]) or pd.isna(row[vereda_col]):
        continue
        
    municipio = str(row[mpio_col]).strip()
    vereda = str(row[vereda_col]).strip()
    
    if municipio and vereda:
        municipios.add(municipio)
        veredas_data.append({
            'municipio': municipio,
            'vereda': vereda
        })

# Sort municipalities alphabetically
municipios_sorted = sorted(list(municipios))

# Create SQL script
with open('insert_municipios_veredas.sql', 'w', encoding='utf-8') as f:
    f.write("-- Script de inserción de municipios y veredas de Boyacá\n")
    f.write("-- Generado automáticamente con capitalización correcta\n\n")
    
    # Insert municipalities
    f.write("-- ============================================\n")
    f.write("-- INSERTAR MUNICIPIOS\n")
    f.write("-- ============================================\n\n")
    
    municipio_map = {}  # Map original name to auto-increment ID (starting from 1)
    for idx, municipio in enumerate(municipios_sorted, start=1):
        capitalized = to_title_case(municipio)
        f.write(f"INSERT INTO municipio (nombre) VALUES ('{capitalized}');\n")
        municipio_map[municipio] = idx  # Assuming IDs start from 1
    
    f.write("\n\n")
    
    # Insert veredas
    f.write("-- ============================================\n")
    f.write("-- INSERTAR VEREDAS\n")
    f.write("-- ============================================\n\n")
    
    # Group veredas by municipality for better organization
    veredas_by_mpio = defaultdict(list)
    for v in veredas_data:
        veredas_by_mpio[v['municipio']].append(v['vereda'])
    
    for municipio in municipios_sorted:
        mpio_capitalized = to_title_case(municipio)
        mpio_id = municipio_map[municipio]  # FK basado en el orden de inserción
        
        f.write(f"\n-- Veredas de {mpio_capitalized}\n")
        
        veredas = sorted(veredas_by_mpio[municipio])
        for vereda in veredas:
            vereda_capitalized = to_title_case(vereda)
            f.write(f"INSERT INTO vereda (nombre, municipio_id) VALUES ('{vereda_capitalized}', {mpio_id});\n")

print(f"✅ SQL script generado exitosamente!")
print(f"📊 Total municipios: {len(municipios_sorted)}")
print(f"📊 Total veredas: {len(veredas_data)}")
print(f"📄 Archivo: insert_municipios_veredas.sql")
