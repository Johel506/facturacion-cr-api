"""
Core enums for Costa Rica electronic document system.
Based on Ministry of Finance specifications v4.4.
"""
from enum import Enum


class DocumentType(str, Enum):
    """Document types according to Costa Rican tax authority."""
    FACTURA_ELECTRONICA = "01"
    NOTA_DEBITO_ELECTRONICA = "02"
    NOTA_CREDITO_ELECTRONICA = "03"
    TIQUETE_ELECTRONICO = "04"
    FACTURA_EXPORTACION = "05"
    FACTURA_COMPRA = "06"
    RECIBO_PAGO = "07"


class IdentificationType(str, Enum):
    """Identification types for Costa Rican entities."""
    CEDULA_FISICA = "01"
    CEDULA_JURIDICA = "02"
    DIMEX = "03"
    NITE = "04"
    EXTRANJERO_NO_DOMICILIADO = "05"
    NO_CONTRIBUYENTE = "06"


class SaleCondition(str, Enum):
    """Sale conditions according to Costa Rican regulations."""
    CONTADO = "01"
    CREDITO = "02"
    CONSIGNACION = "03"
    APARTADO = "04"
    ARRENDAMIENTO_OPCION_COMPRA = "05"
    ARRENDAMIENTO_FUNCION_FINANCIERA = "06"
    COBRO_TERCERO = "07"
    SERVICIOS_ESTADO_CREDITO = "08"
    VENTA_CREDITO_90_DIAS = "10"
    VENTA_MERCANCIA_NO_NACIONALIZADA = "12"
    VENTA_BIENES_USADOS_NO_CONTRIBUYENTE = "13"
    ARRENDAMIENTO_OPERATIVO = "14"
    ARRENDAMIENTO_FINANCIERO = "15"
    OTROS = "99"


class PaymentMethod(str, Enum):
    """Payment methods according to Costa Rican regulations."""
    EFECTIVO = "01"
    TARJETA = "02"
    CHEQUE = "03"
    TRANSFERENCIA = "04"
    RECAUDADO_TERCERO = "05"
    OTROS = "99"


class TaxCode(str, Enum):
    """Tax codes for Costa Rican tax system."""
    IVA = "01"
    SELECTIVO_CONSUMO = "02"
    UNICO_COMBUSTIBLES = "03"
    ESPECIFICO_BEBIDAS_ALCOHOLICAS = "04"
    ESPECIFICO_BEBIDAS_SIN_ALCOHOL = "05"
    PRODUCTOS_TABACO = "06"
    IVA_CALCULO_ESPECIAL = "07"
    IVA_BIENES_USADOS = "08"
    ESPECIFICO_CEMENTO = "12"
    OTROS = "99"


class IVATariffCode(str, Enum):
    """IVA tariff codes for different tax rates."""
    TARIFA_0_PERCENT = "01"
    TARIFA_REDUCIDA_1_PERCENT = "02"
    TARIFA_REDUCIDA_2_PERCENT = "03"
    TARIFA_REDUCIDA_4_PERCENT = "04"
    TRANSITORIO_0_PERCENT = "05"
    TRANSITORIO_4_PERCENT = "06"
    TRANSITORIO_8_PERCENT = "07"
    TARIFA_GENERAL_13_PERCENT = "08"
    TARIFA_REDUCIDA_0_5_PERCENT = "09"
    TARIFA_EXENTA = "10"
    TARIFA_0_SIN_CREDITO = "11"


class ExemptionType(str, Enum):
    """Exemption document types."""
    DGT_AUTHORIZED_PURCHASES = "01"
    DIPLOMATIC_SALES = "02"
    SPECIAL_LAW_AUTHORIZATION = "03"
    GENERAL_LOCAL_AUTHORIZATION = "04"
    ENGINEERING_SERVICES_TRANSITIONAL = "05"
    ICT_TOURISM_SERVICES = "06"
    RECYCLING_TRANSITIONAL = "07"
    FREE_ZONE = "08"
    EXPORT_COMPLEMENTARY_SERVICES = "09"
    MUNICIPAL_CORPORATIONS = "10"
    SPECIFIC_LOCAL_TAX_AUTHORIZATION = "11"
    OTHERS = "99"


class DiscountType(str, Enum):
    """Discount types for line items."""
    ROYALTY = "01"
    ROYALTY_IVA = "02"
    BONUS = "03"
    VOLUME = "04"
    SEASONAL = "05"
    PROMOTIONAL = "06"
    COMMERCIAL = "07"
    FREQUENCY = "08"
    SUSTAINED = "09"
    OTHERS = "99"


class OtherChargeType(str, Enum):
    """Other charge types for additional fees."""
    PARAFISCAL_CONTRIBUTION = "01"
    RED_CROSS_STAMP = "02"
    FIRE_DEPARTMENT_STAMP = "03"
    THIRD_PARTY_COLLECTION = "04"
    EXPORT_COSTS = "05"
    SERVICE_TAX_10_PERCENT = "06"
    PROFESSIONAL_COLLEGE_STAMPS = "07"
    GUARANTEE_DEPOSITS = "08"
    FINES_PENALTIES = "09"
    LATE_INTEREST = "10"
    OTHERS = "99"


class DocumentReferenceType(str, Enum):
    """Document reference types for relationships."""
    ELECTRONIC_INVOICE = "01"
    ELECTRONIC_DEBIT_NOTE = "02"
    ELECTRONIC_CREDIT_NOTE = "03"
    ELECTRONIC_TICKET = "04"
    DISPATCH_NOTE = "05"
    CONTRACT = "06"
    PROCEDURE = "07"
    CONTINGENCY_VOUCHER = "08"
    MERCHANDISE_RETURN = "09"
    MINISTRY_REJECTED = "10"
    RECEIVER_REJECTED_SUBSTITUTE = "11"
    EXPORT_INVOICE_SUBSTITUTE = "12"
    PAST_MONTH_BILLING = "13"
    SPECIAL_REGIME_VOUCHER = "14"
    PURCHASE_INVOICE_SUBSTITUTE = "15"
    NON_DOMICILED_PROVIDER = "16"
    CREDIT_NOTE_TO_PURCHASE_INVOICE = "17"
    DEBIT_NOTE_TO_PURCHASE_INVOICE = "18"
    OTHERS = "99"


class ReferenceCode(str, Enum):
    """Reference codes for document relationships."""
    CANCEL_REFERENCE = "01"
    CORRECT_TEXT = "02"
    REFERENCE_OTHER_DOCUMENT = "04"
    SUBSTITUTE_CONTINGENCY = "05"
    MERCHANDISE_RETURN = "06"
    SUBSTITUTE_ELECTRONIC_VOUCHER = "07"
    ENDORSED_INVOICE = "08"
    FINANCIAL_CREDIT_NOTE = "09"
    FINANCIAL_DEBIT_NOTE = "10"
    NON_DOMICILED_PROVIDER = "11"
    POST_BILLING_EXEMPTION_CREDIT = "12"
    OTHERS = "99"


class CommercialCodeType(str, Enum):
    """Commercial code types for products."""
    SELLER_CODE = "01"
    BUYER_CODE = "02"
    INDUSTRY_ASSIGNED_CODE = "03"
    INTERNAL_USE_CODE = "04"
    OTHERS = "99"


class TransactionType(str, Enum):
    """Transaction types for special tax treatments."""
    NORMAL_SALE = "01"
    SELF_CONSUMPTION_EXEMPT = "02"
    SELF_CONSUMPTION_TAXED = "03"
    SERVICE_SELF_CONSUMPTION_EXEMPT = "04"
    SERVICE_SELF_CONSUMPTION_TAXED = "05"
    MEMBERSHIP_FEE = "06"
    EXEMPT_MEMBERSHIP_FEE = "07"
    CAPITAL_GOODS_FOR_ISSUER = "08"
    CAPITAL_GOODS_FOR_RECEIVER = "09"
    CAPITAL_GOODS_FOR_BOTH = "10"
    EXEMPT_SELF_CONSUMPTION_CAPITAL_GOODS = "11"
    EXEMPT_THIRD_PARTY_CAPITAL_GOODS = "12"
    NO_CONSIDERATION_TO_THIRD_PARTIES = "13"


class InstitutionType(str, Enum):
    """Institution types for exemptions."""
    MINISTERIO_HACIENDA = "01"
    TRIBUNAL_SUPREMO_ELECCIONES = "02"
    CONTRALORIA_GENERAL_REPUBLICA = "03"
    INSTITUTO_COSTARRICENSE_TURISMO = "04"
    COMISION_NACIONAL_EMERGENCIAS = "05"
    INSTITUTO_DESARROLLO_RURAL = "06"
    SENASA = "07"
    SERNAC = "08"
    JUDESUR = "09"
    OTROS_ORGANOS_ESTADO = "10"
    REGIMEN_DIPLOMATICO_CONSULAR = "11"
    ZONA_FRANCA = "12"
    OTHERS = "99"


class IVACondition(str, Enum):
    """IVA conditions for receptor messages."""
    GENERAL_IVA_CREDIT = "01"
    PARTIAL_IVA_CREDIT = "02"
    CAPITAL_GOODS = "03"
    CURRENT_EXPENSE_NO_CREDIT = "04"
    PROPORTIONALITY = "05"


class ReceptorMessageType(int, Enum):
    """Receptor message types."""
    ACCEPTED = 1
    PARTIALLY_ACCEPTED = 2
    REJECTED = 3


class DocumentStatus(str, Enum):
    """Document processing status."""
    BORRADOR = "BORRADOR"
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    PROCESANDO = "PROCESANDO"
    ACEPTADO = "ACEPTADO"
    RECHAZADO = "RECHAZADO"
    ERROR = "ERROR"
    CANCELADO = "CANCELADO"


class TenantPlan(str, Enum):
    """Tenant subscription plans."""
    BASICO = "basico"
    PRO = "pro"
    EMPRESA = "empresa"