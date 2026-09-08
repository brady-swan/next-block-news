"""Isolated transport proof: one explicitly labeled unpublished draft, no newsroom run.

Invoke with --stage only on the intended Typefully service with autopost OFF. Reinvocation
resumes the same journal and cannot create another draft after an ambiguous submission.
Production editorial tables are never opened or populated. Keep the journal for inspection.
This exercises renderer/upload/draft/read-back, not editorial judgment or newsworthiness.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from nbn import config, publisher, publisher_visuals, store, visuals


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",action="store_true")
    args=parser.parse_args()
    if not args.stage:
        parser.error("--stage explicitly authorizes one labeled Typefully test draft")
    if config.AUTOPOST_ENABLED or not config.TYPEFULLY_API_KEY:
        raise RuntimeError("Require autopost OFF and a configured Typefully account")
    directory=Path(config.DATA_DIR)/"smoke"/"visual-0066"
    directory.mkdir(parents=True,exist_ok=True)
    with patch.object(config,"DB_PATH",directory/"nbn.db"), patch.object(config,"TAPE_DIR",directory/"tapes"):
        con=store.connect()
        try:
            row=con.execute("SELECT * FROM publisher_mutations ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                sentence="This image is an NBN capability test, not a news report."
                evidence=[{"fetch_id":"smoke-source","text":sentence,"final_url":"https://example.org/",
                    "retrieval_kind":"direct_fetch","limitations":"Synthetic transport fixture, not real reporting."}]
                asset=visuals.render_asset(con,run_id="smoke:0066-transport",candidate_id="smoke",kind="quote",preset="landscape",
                    spec={"source":"NBN · unpublished transport test","date":"September 2026","passage":sentence,
                        "speaker":"Next Block News test fixture","source_fetch_id":"smoke-source"},
                    evidence=evidence,alt_text=sentence,purpose="Transport QA. Do not publish.")
                body="IMAGE CAPABILITY TEST — DO NOT PUBLISH\n\nThis unpublished draft verifies NBN’s image upload, attachment and alt-text delivery. It is synthetic test material, not news."
                # Explicit operator test fixture, not a fabricated model-editor verdict.
                approval={"verdict":"approve","asset_id":asset["asset_id"],"content_hash":asset["content_hash"],
                    "post_hash":visuals.digest(body),"alt_text":sentence,"credit":asset["metadata"]["credit"],
                    "text_fallback":None,"origin":"operator_transport_fixture"}
                queued=publisher_visuals.queue(con,visual_review=approval,desired_thread=publisher.one_off_x_thread(body,"https://example.org/"),
                    story_key="smoke:0066-transport",operation="create",intended_mode="DRAFT",
                    expected_output_signature=store.canonical_output_state(con,"smoke:0066-transport")["signature"],
                    materialization={"run_id":"smoke:0066-transport","story_id":"smoke","body":body,"receipt_url":"https://example.org/",
                        "klass":"secondary","publisher_backend":"typefully","editor_note":"Operator transport fixture; no editorial claim."})
                if not queued["ok"]: raise RuntimeError("Cannot reserve test intent")
                row=store.publisher_mutation(con,queued["mutation_id"])
            row=dict(row)
            status=row["state"] if row["state"] in {"confirmed","definite_failure","needs_owner_review"} else publisher_visuals.process_one(con,row)
            row=dict(store.publisher_mutation(con,row["mutation_id"]))
            data=json.loads(row["materialization_json"])
            print(json.dumps({"state":status,"journal_state":row["state"],"draft_id":data.get("acknowledged_draft_id"),
                "asset_id":data["visual_review"]["asset_id"],"payload_fingerprint":row["desired_fingerprint"],
                "remote_version":data.get("remote_version"),"error_kind":row.get("error_kind"),
                "journal":str(directory/"nbn.db"),"autopost":config.AUTOPOST_ENABLED}))
        finally:
            con.close()


if __name__=="__main__": main()
