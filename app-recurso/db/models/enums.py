import enum

from sqlalchemy import Enum

# Tipos ENUM nativos de PostgreSQL. create_all crea el tipo la primera vez;
# agregar un valor después requiere: ALTER TYPE <tipo> ADD VALUE '<VALOR>'.


class TipoActo(str, enum.Enum):
    AUTO_ADMITE = "AUTO_ADMITE"
    REQUERIMIENTO = "REQUERIMIENTO"
    RECONOCE_TERCERO = "RECONOCE_TERCERO"
    DECISION = "DECISION"
    RECURSO = "RECURSO"
    APRUEBA_MEMORIAS = "APRUEBA_MEMORIAS"
    APRUEBA_OBRAS = "APRUEBA_OBRAS"


class TipoVinculo(str, enum.Enum):
    SOLICITANTE = "SOLICITANTE"
    TERCERO_INTERVINIENTE = "TERCERO_INTERVINIENTE"


class UsoAgua(str, enum.Enum):
    DOMESTICO = "DOMESTICO"
    PECUARIO = "PECUARIO"
    ABREVADERO = "ABREVADERO"
    AGRICOLA = "AGRICOLA"
    RIEGO = "RIEGO"
    INDUSTRIAL = "INDUSTRIAL"
    ACUICULTURA = "ACUICULTURA"
    SILVICULTURA = "SILVICULTURA"
    RECREATIVO = "RECREATIVO"
    INSTITUCIONAL = "INSTITUCIONAL"
    OTRO = "OTRO"


class TipoDecision(str, enum.Enum):
    OTORGADA = "OTORGADA"
    NEGADA = "NEGADA"
    DESISTIDA = "DESISTIDA"


class ResultadoRecurso(str, enum.Enum):
    REPONE = "REPONE"
    CONFIRMA = "CONFIRMA"
    MODIFICA = "MODIFICA"
    ADICIONA = "ADICIONA"


tipo_acto_enum = Enum(TipoActo, name="tipo_acto")
tipo_vinculo_enum = Enum(TipoVinculo, name="tipo_vinculo")
uso_agua_enum = Enum(UsoAgua, name="uso_agua")
tipo_decision_enum = Enum(TipoDecision, name="tipo_decision")
resultado_recurso_enum = Enum(ResultadoRecurso, name="resultado_recurso")
