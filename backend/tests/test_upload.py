import pytest
import io
import shutil
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from conftest import TestingSessionLocal
from app.models.beneficiary import Beneficiary
from app.models.company import CompanyDemo
from app.models.invoice import Invoice
from app.services import extraction as extraction_module
from app.services.extraction import ExtractionResult
import app.api.v1.upload as upload_module


def _make_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_text_pdf(
    text: str = (
        "Beneficiario: Taller Demo Importe: 750.00 USD "
        "Factura: FT-2026-01 Fecha de emision: 18/10/2026 "
        "Concepto: Servicio de prueba"
    ),
) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
    })
    content = DecodedStreamObject()
    content.set_data(f"BT /F1 12 Tf 36 750 Td ({text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def _seed_company(db):
    if not db.query(CompanyDemo).filter(CompanyDemo.id == "co_upload_01").first():
        db.add(CompanyDemo(id="co_upload_01", name="Co Upload", currency_base="USD"))
        db.commit()


class FakeExtraction:
    def __init__(self, source_type="pdf", raw_text="", confidence=0.95, ocr_available=False, ocr_warning=None):
        self.source_type = source_type
        self.file_name = "factura.pdf"
        self.file_hash = "sha256:faketest"
        self.file_path = "/tmp/fake/factura.pdf"
        self.mime_type = "application/pdf"
        self.size_bytes = 100
        self.raw_text = raw_text
        self.extraction_confidence = confidence
        self.ocr_available = ocr_available
        self.ocr_warning = ocr_warning
        self.ocr_used = False
        self.fields = {
            "beneficiary_name": "Proveedor de prueba",
            "invoice_number": None,
            "amount": None,
            "currency": None,
            "issue_date": None,
            "due_date": None,
            "description": "",
        }


def _fake_extract(content, file_name):
    return FakeExtraction()


@pytest.fixture
def patch_extract(monkeypatch):
    monkeypatch.setattr(upload_module, "extract_file", _fake_extract)


def test_upload_pdf_creates_pending_invoice(client, db_session, patch_extract):
    from app.models.audit_log import AuditLog

    _seed_company(db_session)
    pdf_bytes = _make_pdf_bytes()

    files = {"file": ("factura.pdf", pdf_bytes, "application/pdf")}
    data = {"company_id": "co_upload_01"}
    r = client.post("/api/v1/invoices/upload", files=files, data=data)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "PENDING"
    assert body["source_type"] == "pdf"
    assert body["file_name"] == "factura.pdf"
    assert body["file_hash"].startswith("sha256:")
    assert body["ocr_available"] is False
    event = db_session.query(AuditLog).filter_by(
        action="INVOICE_UPLOADED", entity_id=body["id"]
    ).one()
    assert event.actor_id == "demo_user"
    assert event.event_metadata["file_name"] == "factura.pdf"
    assert event.event_metadata["file_hash"] == body["file_hash"]
    assert "raw_text" not in event.event_metadata


def test_upload_rejected_extension(client, db_session):
    _seed_company(db_session)
    files = {"file": ("malware.exe", b"\x00\x01", "application/octet-stream")}
    data = {"company_id": "co_upload_01"}
    r = client.post("/api/v1/invoices/upload", files=files, data=data)
    assert r.status_code == 400, r.text


def test_upload_with_beneficiary_sets_company_and_beneficiary(
    client, db_session, patch_extract
):
    _seed_company(db_session)
    db_session.add(
        Beneficiary(
            id="ben_upload_01",
            company_id="co_upload_01",
            name="Proveedor de prueba",
            normalized_name="proveedor de prueba",
            allowed=True,
            reference_code="PRO-001",
            category="Pruebas",
        )
    )
    db_session.commit()
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}

    response = client.post(
        "/api/v1/invoices/upload",
        files=files,
        data={"beneficiary_id": "ben_upload_01"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["beneficiary_id"] == "ben_upload_01"
    invoice = db_session.query(Invoice).filter_by(id=response.json()["id"]).one()
    assert invoice.company_id == "co_upload_01"
    assert invoice.beneficiary_id == "ben_upload_01"


def test_upload_unknown_beneficiary_returns_not_found(client, db_session, patch_extract):
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}

    response = client.post(
        "/api/v1/invoices/upload",
        files=files,
        data={"beneficiary_id": "PAP-002"},
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "Proveedor no encontrado"
    assert db_session.query(Invoice).count() == 0


def test_upload_unknown_company_returns_not_found(client, db_session, patch_extract):
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}
    data = {"company_id": "PAP-002"}

    r = client.post("/api/v1/invoices/upload", files=files, data=data)

    assert r.status_code == 404, r.text
    assert r.json()["detail"] == "Empresa no encontrada"
    assert db_session.query(Invoice).count() == 0


def test_upload_without_company_uses_single_demo_company(client, db_session, patch_extract):
    _seed_company(db_session)
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}
    r = client.post("/api/v1/invoices/upload", files=files, data={})
    assert r.status_code == 201, r.text
    assert r.json()["company_id"] == "co_upload_01"


def test_upload_without_company_requires_choice_if_multiple_companies_exist(
    client, db_session, patch_extract
):
    _seed_company(db_session)
    db_session.add(CompanyDemo(id="co_upload_02", name="Co Upload 2", currency_base="USD"))
    db_session.commit()
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}

    response = client.post("/api/v1/invoices/upload", files=files)

    assert response.status_code == 422, response.text
    assert "empresa única" in response.json()["detail"]


def test_upload_manual_details_override_extracted_values(client, db_session, patch_extract):
    _seed_company(db_session)
    db_session.add(
        Beneficiary(
            id="ben_upload_02",
            company_id="co_upload_01",
            name="Proveedor manual",
            normalized_name="proveedor manual",
            allowed=True,
        )
    )
    db_session.commit()
    files = {"file": ("factura.pdf", _make_pdf_bytes(), "application/pdf")}

    response = client.post(
        "/api/v1/invoices/upload",
        files=files,
        data={
            "beneficiary_id": "ben_upload_02",
            "invoice_number": "MAN-2026-01",
            "amount": "750.00",
            "currency": "USD",
            "issue_date": "2026-10-18",
            "due_date": "2026-11-18",
            "description": "Capturada manualmente",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["beneficiary_id"] == "ben_upload_02"
    assert body["invoice_number"] == "MAN-2026-01"
    assert float(body["amount"]) == 750
    assert body["issue_date"] == "2026-10-18"
    assert body["due_date"] == "2026-11-18"
    assert body["description"] == "Capturada manualmente"
    assert body["extracted"]["_field_sources"]["amount"] == "manual"


def test_reextract_without_file(client, db_session):
    _seed_company(db_session)
    db = TestingSessionLocal()
    db.add(
        Invoice(
            id="inv_no_file", company_id="co_upload_01", source_type="manual",
            status="PENDING", file_path=None,
        )
    )
    db.commit()
    db.close()

    r = client.post("/api/v1/invoices/inv_no_file/extract")
    assert r.status_code == 400, r.text


def test_upload_text_pdf_extracts_fields_and_reextracts(
    client, db_session, monkeypatch, tmp_path
):
    _seed_company(db_session)
    db_session.add(
        Beneficiary(
            id="ben_taller_demo",
            company_id="co_upload_01",
            name="Taller Demo",
            normalized_name="taller demo",
            allowed=True,
            reference_code="TAL-001",
            category="Servicios",
        )
    )
    db_session.commit()
    monkeypatch.setattr(extraction_module, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("factura.pdf", _make_text_pdf(), "application/pdf")},
        data={"company_id": "co_upload_01"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["extracted"]["beneficiary_name"] == "Taller Demo"
    assert body["extracted"]["invoice_number"] == "FT-2026-01"
    assert body["extracted"]["amount"] == "750.00"
    assert body["extracted"]["currency"] == "USD"
    assert body["extracted"]["issue_date"] == "2026-10-18"
    assert body["extracted"]["description"] == "Servicio de prueba"
    assert body["beneficiary_id"] == "ben_taller_demo"
    invoice = db_session.query(Invoice).filter_by(id=body["id"]).one()
    assert invoice.status == "PENDING"
    assert invoice.amount == 750.0
    assert invoice.invoice_number == "FT-2026-01"

    reextract = client.post(f"/api/v1/invoices/{body['id']}/extract")
    assert reextract.status_code == 200, reextract.text
    refreshed_invoice = db_session.query(Invoice).filter_by(id=body["id"]).one()
    assert refreshed_invoice.extracted["amount"] == "750.00"
    assert refreshed_invoice.issue_date.isoformat() == "2026-10-18"


def test_upload_text_pdf_extracts_common_alternate_labels(
    client, db_session, monkeypatch, tmp_path
):
    _seed_company(db_session)
    db_session.add(
        Beneficiary(
            id="ben_mantenimiento",
            company_id="co_upload_01",
            name="Mantenimiento Pacífico S.A.S.",
            normalized_name="mantenimiento pacifico sas",
            allowed=True,
        )
    )
    db_session.commit()
    monkeypatch.setattr(extraction_module, "UPLOAD_DIR", tmp_path)
    pdf_text = (
        "Razon social: Mantenimiento Pacifico S.A.S. "
        "Nro de factura: FAC-2026-0081 "
        "Fecha de emision: 18/10/2026 "
        "Fecha limite de pago: 18/11/2026 "
        "Total a pagar: USD 750.00 "
        "Descripcion: Mantenimiento preventivo"
    )

    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("factura.pdf", _make_text_pdf(pdf_text), "application/pdf")},
        data={"company_id": "co_upload_01"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["extracted"]["beneficiary_name"] == "Mantenimiento Pacifico S.A.S."
    assert body["extracted"]["invoice_number"] == "FAC-2026-0081"
    assert body["extracted"]["amount"] == "750.00"
    assert body["extracted"]["currency"] == "USD"
    assert body["extracted"]["issue_date"] == "2026-10-18"
    assert body["extracted"]["due_date"] == "2026-11-18"
    assert body["extracted"]["description"] == "Mantenimiento preventivo"
    assert body["beneficiary_id"] == "ben_mantenimiento"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract no está instalado")
def test_upload_image_ocr_parses_fields_end_to_end(
    client, db_session, monkeypatch, tmp_path
):
    _seed_company(db_session)
    db_session.add(
        Beneficiary(
            id="ben_ocr_taller",
            company_id="co_upload_01",
            name="Taller Demo",
            normalized_name="taller demo",
            allowed=True,
        )
    )
    db_session.commit()
    monkeypatch.setattr(extraction_module, "UPLOAD_DIR", tmp_path)

    image = Image.new("RGB", (1800, 700), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=56)
    for index, line in enumerate(
        (
            "Proveedor: Taller Demo",
            "Nro de factura: TAL-2026-101",
            "Fecha de emision: 18/10/2026",
            "Fecha de vencimiento: 18/11/2026",
            "Total a pagar: USD 750.00",
            "Concepto: Mantenimiento",
        )
    ):
        draw.text((50, 35 + index * 100), line, fill="black", font=font)
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    response = client.post(
        "/api/v1/invoices/upload",
        files={"file": ("factura.png", image_bytes.getvalue(), "image/png")},
        data={"company_id": "co_upload_01"},
    )

    assert response.status_code == 201, response.text
    fields = response.json()["extracted"]
    assert fields["beneficiary_name"] == "Taller Demo"
    assert fields["invoice_number"] == "TAL-2026-101"
    assert fields["amount"] == "750.00"
    assert fields["currency"] == "USD"
    assert fields["issue_date"] == "2026-10-18"
    assert fields["due_date"] == "2026-11-18"
    assert fields["description"] == "Mantenimiento"
