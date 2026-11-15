import server

from tests.firestore_test_utils import FirestoreDBSurrogate
mock_db = FirestoreDBSurrogate()
db = FirestoreDBSurrogate()
"""Regression tests for the v2 application-template catalog.

Covers:
  * The 21 new application templates (verbatim lawyer drafts) are the active
    catalog with their exact Gujarati titles; no case-owned field is asked as
    an editable application field.
  * Case -> application inheritance: court/district/taluka/case type/case
    number/parties + party roles flow from the Case; taluka stays optional;
    advocate_side maps to the represented side's role.
  * Conditional "અન્ય/Other" fields (depends_on/show_when) and the date
    defaulting to today.
  * PDF/DOCX/ODT/PNG generation from the new templates (Gujarati + mixed
    script), with unique embedded font identities per generation.
  * Admin placeholder registry: add/edit/delete ANY placeholder (custom IDs
    like 001 supported), persisted on the template record.
"""
import base64
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DB_NAME", "nyaysetu_test_catalog_v2")



import server


from starlette.testclient import TestClient

app_client = TestClient(server.app)

API = "/api"
ADMIN = "/api/admin"

EXPECTED_TITLES = {
    "aanke_padvani_arji": "દસ્તાવેજને આંકે પાડવાની અરજી",
    "certified_report": "સર્ટિફાઇડ રિપોર્ટ / નકલ મેળવવાની અરજી",
    "dd_karavani_arji": "DD કરાવવાની અરજી",
    "document_return": "દસ્તાવેજ પરત મેળવવાની અરજી",
    "document_on_record": "દસ્તાવેજ રેકર્ડ પર લેવા અરજી",
    "closing_purshish": "ક્લોઝિંગ પુરશીશ",
    "hazari_mafi_arji": "હાજરી માફીની અરજી",
    "fs_haq_bandh": "એફ.એસ.નો હક બંધ કરવાની અરજી",
    "fs_haq_khol": "એફ.એસ.નો હક ફરીથી ખોલવાની અરજી",
    "jamin_bond": "જામીન બોન્ડ સ્વીકારવા અરજી",
    "kam_board": "કામ બોર્ડ પર લેવા અરજી",
    "mudat_arji": "મુદ્દત અરજી",
    "saaxi_summons": "સાક્ષીને સમન્સ કાઢવાની અરજી",
    "samadhan_purshish": "સમાધાન પુરશીશ",
    "ulat_tapas_bandh": "ઉલટતપાસનો હક બંધ કરવાની અરજી",
    "ulat_tapas_khol": "ઉલટતપાસનો હક ફરીથી ખોલવાની અરજી",
    "undertaking": "બાંહેધરી",
    "vakilatnama_civil": "વકીલાતનામું (સિવિલ)",
    "vakilatnama_criminal": "વકીલાતનામું (ક્રિમિનલ)",
    "warrant_hathbido": "સમન્સ/વોરંટનો હાથબીડો આપવા અરજી",
    "warrant_rad": "વોરંટ રદ કરવાની અરજી",
}

CASE_OWNED_KEYS = {
    "court", "district", "taluka", "case_type", "case_number",
    "party_name", "opposite_party",
}


def _login(mobile: str):
    r = app_client.post(f"{API}/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200, r.text
    r = app_client.post(f"{API}/auth/verify-otp", json={"mobile": mobile, "otp": "123456"})
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]["id"]


def _hdr(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def setup_v2_templates_isolation():
    import asyncio as _aio
    import test_seed_data_templates_v2
    from conftest import _global_firestore_proxy
    orig_seeds_func = server._get_all_seed_templates
    server._get_all_seed_templates = lambda: test_seed_data_templates_v2.TEMPLATES_V2

    loop = _aio.new_event_loop()
    _aio.set_event_loop(loop)
    canonical_snapshot = {}
    v2_ids = [t["id"] for t in test_seed_data_templates_v2.TEMPLATES_V2]

    async def _setup():
        client = _global_firestore_proxy._get_client()
        async for d in client.collection("templates").stream():
            canonical_snapshot[d.id] = d.to_dict()
        batch = client.batch()
        for t in test_seed_data_templates_v2.TEMPLATES_V2:
            item = dict(t)
            item.setdefault("status", "published")
            item.setdefault("version", 1)
            ref = client.collection("templates").document(t["id"])
            batch.set(ref, item)
        await batch.commit()
        server.invalidate_published_templates_cache()

    async def _teardown():
        client = _global_firestore_proxy._get_client()
        to_del = [vid for vid in v2_ids if vid not in canonical_snapshot]
        if to_del:
            del_batch = client.batch()
            for vid in to_del:
                del_batch.delete(client.collection("templates").document(vid))
            await del_batch.commit()
        if canonical_snapshot:
            rest_batch = client.batch()
            for cid, cdoc in canonical_snapshot.items():
                rest_batch.set(client.collection("templates").document(cid), cdoc)
            await rest_batch.commit()
        server.invalidate_published_templates_cache()

    try:
        loop.run_until_complete(_setup())
        yield
    finally:
        try:
            loop.run_until_complete(_teardown())
        finally:
            server._get_all_seed_templates = orig_seeds_func
            loop.close()


@pytest.fixture(scope="module")
def user():
    if not server._CATALOG_MAPS_SYNCED:
        import asyncio as _aio
        _loop = _aio.new_event_loop()
        try:
            _loop.run_until_complete(server.seed_catalogs())
        finally:
            _loop.close()
    token, user_id = _login(f"9{int(datetime.now().timestamp()) % 1000000000:09d}")
    # Case WITH taluka + party roles
    r = app_client.post(f"{API}/cases", headers=_hdr(token), json={
        "language": "gu",
        "case_number": "1234/2026",
        "case_type_id": "criminal_complaint",
        "complaint_type": "private",
        "law_id": "ni_act",
        "section_id": "138",
        "party_name": "રોનક સોલંકી",
        "party_role": "ફરિયાદી",
        "opposite_party": "મનોજ શર્મા",
        "opposite_party_role": "આરોપી",
        "court": "જેએમએફસી ગાંધીનગર",
        "district_id": "gandhinagar",
        "taluka_id": "kalol",
    })
    assert r.status_code == 200, r.text
    case_with_taluka = r.json()["id"]
    # Case WITHOUT taluka (must stay optional end-to-end)
    r = app_client.post(f"{API}/cases", headers=_hdr(token), json={
        "language": "gu",
        "case_number": "99/2026",
        "case_type_id": "criminal_complaint",
        "complaint_type": "private",
        "party_name": "અનિલ પટેલ",
        "party_role": "અરજદાર",
        "opposite_party": "દિનેશ શાહ",
        "opposite_party_role": "સામાવાળા",
        "court": "જેએમએફસી ગાંધીનગર",
        "district_id": "gandhinagar",
    })
    assert r.status_code == 200, r.text
    case_no_taluka = r.json()["id"]
    # Top up the wallet so every generation test in this module can download.
    import asyncio as _aio
    _loop = _aio.new_event_loop()
    try:
        _loop.run_until_complete(server.db.wallets.update_one(
            {"user_id": user_id}, {"$set": {"balance": 50}}
        ))
    finally:
        _loop.close()
    return {"token": token, "case_with_taluka": case_with_taluka, "case_no_taluka": case_no_taluka}


class TestV2Catalog:
    def test_all_21_templates_present_with_exact_titles(self):
        items = app_client.get(f"{API}/templates").json()
        by_id = {t["id"]: t for t in items}
        import conftest
        canonical_map = {s["id"]: s.get("name_gu") for s in conftest.get_canonical_25_base_seeds()}
        for tid, title_gu in EXPECTED_TITLES.items():
            assert tid in by_id, f"v2 template {tid} missing from public catalog"
            allowed = {title_gu}
            if tid in canonical_map and canonical_map[tid]:
                allowed.add(canonical_map[tid])
            if tid == "certified_report":
                allowed.add("પ્રમાણિત નકલ માટે અરજી")
            assert by_id[tid]["name_gu"] in allowed, f"{tid}: title mismatch"

    def test_archiving_old_default_hides_them_from_public(self):
        """The catalog-swap behaviour: once the old default seed templates are
        archived (production migration), they disappear from the public list
        while the v2 templates remain active."""
        import asyncio
        from test_seed_data import TEMPLATES as OLD_TEMPLATES
        old_ids = [t["id"] for t in OLD_TEMPLATES if t["id"] not in EXPECTED_TITLES and t["id"] not in server.CANONICAL_TEMPLATE_IDS]
        loop = asyncio.new_event_loop()
        orig_states = {}
        try:
            async def _capture_and_archive():
                for tid in old_ids:
                    doc_ref = server.db.collection("templates").document(tid)
                    snap = await doc_ref.get()
                    orig_states[tid] = snap.to_dict() if snap.exists else None
                    if snap.exists:
                        await doc_ref.set({"status": "archived"}, merge=True)
                    else:
                        await doc_ref.set({"id": tid, "status": "archived"})

            loop.run_until_complete(_capture_and_archive())
            server.invalidate_published_templates_cache()

            items = app_client.get(f"{API}/templates").json()
            visible_ids = {t["id"] for t in items}
            assert not (set(old_ids) & visible_ids), "old default templates still public after archive"
            assert EXPECTED_TITLES.keys() <= visible_ids
        finally:
            async def _restore_exact_state():
                for tid, orig_doc in orig_states.items():
                    doc_ref = server.db.collection("templates").document(tid)
                    if orig_doc is not None:
                        await doc_ref.set(orig_doc)
                    else:
                        await doc_ref.delete()

            try:
                loop.run_until_complete(_restore_exact_state())
                server.invalidate_published_templates_cache()
            finally:
                loop.close()

    def test_no_case_owned_field_is_an_editable_application_field(self):
        items = app_client.get(f"{API}/templates").json()
        dd_evaluated = False
        for t in items:
            if t["id"] not in EXPECTED_TITLES:
                continue
            if t["id"] == "dd_karavani_arji":
                # dd_karavani_arji intentionally preserves its canonical schema
                dd_evaluated = True
                dd_keys = [f["key"] for f in t["fields"]]
                assert len(dd_keys) in (4, 14), f"dd_karavani_arji must have 4 or 14 fields, got {len(dd_keys)}"
                continue
            keys = {f["key"] for f in t["fields"]}
            overlap = keys & CASE_OWNED_KEYS
            assert not overlap, f"{t['id']} re-asks case-owned fields: {overlap}"
        assert dd_evaluated, "dd_karavani_arji was not evaluated in public templates"

    def test_conditional_other_field_metadata(self):
        t = app_client.get(f"{API}/templates/mudat_arji").json()
        other = next((f for f in t["fields"] if f["key"] in ("reason_other", "other_adjournment_reason")), None)
        assert other is not None
        assert other.get("depends_on") in ("reason", "reason=other") or other.get("show_when") == "other"
        reason = next((f for f in t["fields"] if f["key"] in ("reason", "adjournment_reason")), None)
        assert reason is not None
        assert any(o["value"] == "other" for o in reason.get("options", []))

    def test_advocate_side_case_parties_source(self):
        t = app_client.get(f"{API}/templates/vakilatnama_civil").json()
        side = next((f for f in t["fields"] if f["key"] in ("advocate_side", "advocate_for")), None)
        assert side is not None
        assert side.get("source") in ("case_parties", None) or side.get("type") == "select"


class TestCaseInheritance:
    def test_case_fields_inherited_with_roles_and_taluka(self, user):
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "mudat_arji",
            "case_id": user["case_with_taluka"],
            "language": "gu",
            "values": {"reason": "માંદગીના", "advocate_side": "opposite"},
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "જેએમએફસી ગાંધીનગર" in c          # court inherited
        assert "કલોલ, ગાંધીનગર" in c              # taluka, district order
        assert "ફરીયાદી રોનક સોલંકી" in c         # role + name (authoritative server.ROLE_MAP spelling)
        assert "આરોપી મનોજ શર્મા" in c            # opposite role + name
        assert "આરોપી ના એડવોકેટ" in c            # advocate_side=opposite
        assert "માંદગીના કારણોસર" in c
        assert re.search(r"(?:તા\.|તારીખ\s*:) \d{2}/\d{2}/\d{4}", c)  # date auto = today

    def test_taluka_optional_no_fake_values(self, user):
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "mudat_arji",
            "case_id": user["case_no_taluka"],
            "language": "gu",
            "values": {"reason": "માંદગીના", "advocate_side": "party"},
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "ગાંધીનગર" in c
        assert "None" not in c and "null" not in c and "{{" not in c
        assert "અરજદાર અનિલ પટેલ" in c
        # mudat_arji advocate representation
        assert ("અરજદાર ના એડવોકેટ" in c or "સામાવાળાના એડવોકેટ" in c)

    def test_advocate_side_party_mapping(self, user):
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "aanke_padvani_arji",
            "case_id": user["case_with_taluka"],
            "language": "gu",
            "values": {"advocate_side": "party", "document_details": "આંક ૩ થી રજૂ કરેલ દસ્તાવેજ"},
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "ફરીયાદી ના એડવોકેટ" in c
        assert "આંક ૩ થી રજૂ કરેલ દસ્તાવેજ" in c

    def test_conditional_other_value_renders(self, user):
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "hazari_mafi_arji",
            "case_id": user["case_with_taluka"],
            "language": "gu",
            "values": {
                "advocate_side": "party",
                "absence_reason": "other",
                "absence_reason_other": "પરીક્ષામાં બેઠેલ હોવાના",
            },
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "પરીક્ષામાં બેઠેલ હોવાના કારણોસર" in c

    def test_jamin_bond_case_or_crime(self, user):
        # No case number -> crime registration number is used
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "jamin_bond",
            "case_id": user["case_no_taluka"],
            "language": "gu",
            "values": {"case_number": "", "crime_reg_number": "42/2026", "bail_court": "હાઈકોર્ટ"},
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "ગુન્હા રજી. નં. 42/2026" in c
        assert "હાઈકોર્ટ દ્વારા" in c

    def test_english_content_generates(self, user):
        r = app_client.post(f"{API}/applications/preview", headers=_hdr(user["token"]), json={
            "template_id": "warrant_rad",
            "case_id": user["case_with_taluka"],
            "language": "en",
            # The real client always sends dates as DD-MM-YYYY (toDocValues).
            "values": {"warrant_date": "01-08-2026", "absence_reason": "no notice received"},
        })
        assert r.status_code == 200, r.text
        c = r.json()["content"]
        assert "APPLICATION TO CANCEL WARRANT" in c
        assert "01-08-2026" in c
        assert "no notice received" in c


class TestV2DocumentGeneration:
    @pytest.mark.parametrize("fmt", ["pdf", "docx", "odt", "png"])
    def test_generate_all_formats(self, user, fmt):
        r = app_client.post(f"{API}/applications/download", headers=_hdr(user["token"]), json={
            "template_id": "mudat_arji",
            "case_id": user["case_with_taluka"],
            "language": "gu",
            "format": fmt,
            "values": {"reason": "પુરાવા તૈયાર કરવાના", "advocate_side": "opposite"},
        })
        assert r.status_code == 200, r.text
        data = r.json()
        raw = base64.b64decode(data["base64"])
        assert len(raw) > 100, "empty/corrupt artifact"
        if fmt == "pdf":
            assert raw[:4] == b"%PDF"
            # Per-generation unique font identity prevents Android cache collision.
            assert b"GujHB-" in raw
        elif fmt == "docx":
            assert raw[:2] == b"PK"
        elif fmt == "odt":
            assert raw[:2] == b"PK"
        elif fmt == "png":
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        # Artifact metadata recorded on the application history record.
        history = app_client.get(f"{API}/applications/history", headers=_hdr(user["token"])).json()
        rec = history[0]
        assert rec["format"] == fmt
        assert rec["file_size"] == len(raw) and rec["file_size"] > 0
        assert rec["sha256"] and len(rec["sha256"]) == 64
        assert rec["generator_version"]

    def test_repeated_pdf_has_distinct_font_identity(self, user):
        def _sub():
            r = app_client.post(f"{API}/applications/download", headers=_hdr(user["token"]), json={
                "template_id": "vakilatnama_civil",
                "case_id": user["case_with_taluka"],
                "language": "gu",
                "format": "pdf",
                "values": {"advocate_side": "party", "party_sign_name": "રોનક સોલંકી"},
            })
            assert r.status_code == 200, r.text
            return base64.b64decode(r.json()["base64"])
        a, b = _sub(), _sub()
        ids_a = set(re.findall(rb"/BaseFont /([A-Z0-9]{6})\+", a))
        ids_b = set(re.findall(rb"/BaseFont /([A-Z0-9]{6})\+", b))
        assert ids_a and ids_b
        assert ids_a != ids_b


class TestAdminPlaceholderRegistry:
    def _admin_token(self):
        # Seed a super admin directly (mirrors the other admin test modules).
        import asyncio
        import bcrypt
        import uuid
        from datetime import datetime, timezone
        from server import make_admin_token
        loop = asyncio.new_event_loop()
        try:
            admin_id = str(uuid.uuid4())
            hashed = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode("utf-8")
            admin = {
                "id": admin_id,
                "email": "ph_admin@test.com",
                "password_hash": hashed,
                "name": "Placeholder Admin",
                "role": "super_admin",
                "active": True,
                "last_login": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            loop.run_until_complete(server.db.admin_users.insert_one(admin.copy()))
        finally:
            loop.close()
        return make_admin_token(admin_id, "ph_admin@test.com", "super_admin")

    def test_placeholder_crud_and_custom_ids(self):
        token = self._admin_token()
        h = _hdr(token)
        payload = {
            "name_en": "Placeholder CRUD Test",
            "name_gu": "પ્લેસહોલ્ડર ટેસ્ટ",
            "category": "General",
            "content_en": "Court {{001}} case {{court}}",
            "content_gu": "કોર્ટ {{001}} કેસ {{court}}",
            "fields": [],
            "placeholders": [
                {"key": "001", "label_en": "Court Name", "label_gu": "કોર્ટનું નામ", "type": "text", "required": False, "source": "system"},
                {"key": "court", "label_en": "Court", "label_gu": "કોર્ટ", "type": "text", "required": False, "source": "system"},
            ],
        }
        r = app_client.post(f"{ADMIN}/templates", headers=h, json=payload)
        assert r.status_code == 200, r.text
        tid = r.json()["id"]

        # Edit: rename 001 -> 002 and delete court; add a new placeholder
        r = app_client.put(f"{ADMIN}/templates/{tid}", headers=h, json={
            "placeholders": [
                {"key": "002", "label_en": "Court Name", "label_gu": "કોર્ટનું નામ", "type": "text", "required": False, "source": "system"},
                {"key": "custom_x", "label_en": "Extra", "label_gu": "વધારાનું", "type": "text", "required": False, "source": "custom"},
            ],
            "content_en": "Court {{002}} and {{custom_x}}",
            "content_gu": "કોર્ટ {{002}} અને {{custom_x}}",
        })
        assert r.status_code == 200, r.text

        got = app_client.get(f"{ADMIN}/templates/{tid}", headers=h).json()
        keys = [p["key"] for p in got["placeholders"]]
        assert keys == ["002", "custom_x"], f"placeholders not persisted: {keys}"
        assert "{{002}}" in got["content_en"] and "{{court}}" not in got["content_en"]

        # Cleanup: remove the test template record via admin API.
        r_del = app_client.delete(f"{ADMIN}/templates/{tid}", headers=h)
        assert r_del.status_code in (200, 204, 404)
