"""Presentation trace integrity, ambiguous identities and safe source staging."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from analyze_skate3_probe import analyze, KINDS
from stage_skate3_probe import ROOT, SKATE_PIN, THUG_PIN, stage, git, runtime_files


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name)/"trace.jsonl"
        self.records = [{"kind": "header", "schema_version": 1, "scope": "presentation-only",
                         "units": "meter", "player_identity": "unresolved", "simulation_tick": "unresolved",
                         "skate3_commit": SKATE_PIN}]
        self.epoch = 0

    def tearDown(self):
        self.folder.cleanup()

    def event(self, kind, entity=0x10000, x=None):
        index=len(self.records)-1
        self.records.append({"kind": kind, "sequence": index, "mono_ns": index*1000000,
                             "render_epoch": self.epoch, "host_thread_tag": 123,
                             "entity": entity, "hook": KINDS[kind], "caller": 0x82012340,
                             "detail": 0, "pose_status": 0 if x is None else 1,
                             **({"world_rows": [1,0,0,x,0,1,0,0,0,0,1,0]} if x is not None else {})})
        if kind=="swap_begin":
            self.epoch+=1

    def write(self, **summary):
        records=copy.deepcopy(self.records)
        records.append({"kind": "summary", "written_events": len(records)-1, "accepted_events": len(records)-1,
                        "dropped_events": 0, "invalid_matrices": 0, "limit_reached": False,
                        "io_error": False, "worker_error": False, **summary})
        self.path.write_text("".join(json.dumps(r)+"\n" for r in records))
        return analyze(self.path)

    def test_moving_npc_is_not_selected_as_player(self):
        for entity in [0x10000,0x20000]:
            self.event("view_add",entity)
            self.event("bind_cac",entity,x=0)
        self.event("jobs_end_exit",0x10000,x=1)
        self.event("jobs_end_exit",0x20000,x=100)
        result=self.write()
        self.assertTrue(result["recording_complete"])
        self.assertEqual(result["player_identity"],"unresolved")
        self.assertEqual([a["observed_path_m"] for a in result["actors"]],[1,100])
        self.assertNotIn("selected_actor",result)

    def test_paused_repeated_poses_and_swaps_do_not_prove_ticks(self):
        for _ in range(3):
            self.event("swap_begin",0)
            self.event("jobs_end_exit",x=4)
        result=self.write()
        self.assertEqual(result["accepted_swaps"],3)
        self.assertEqual(result["simulation_tick"],"unresolved")
        self.assertEqual(result["actors"][0]["pose_changes"],0)

    def test_address_reuse_splits_observed_generations(self):
        self.event("view_add",x=0)
        self.event("view_remove")
        self.event("view_add",x=100)
        result=self.write()
        self.assertEqual([a["observed_generation"] for a in result["actors"]],[1,2])
        self.assertEqual([a["observed_path_m"] for a in result["actors"]],[0,0])

    def test_loss_limit_and_missing_footer_are_incomplete(self):
        self.event("bind_skater",x=0)
        for summary in [{"dropped_events": 1}, {"limit_reached": True},
                        {"accepted_events": 2}, {"io_error": True}, {"worker_error": True}]:
            self.assertFalse(self.write(**summary)["recording_complete"])
        self.path.write_text("".join(json.dumps(r)+"\n" for r in self.records)+"{\"kind\":")
        self.assertFalse(analyze(self.path)["recording_complete"])

    def test_bad_rows_and_misleading_header_rejected(self):
        self.event("bind_cac",x=float("nan"))
        with self.assertRaises(ValueError):
            self.write()
        self.records[-1]["world_rows"][3]=30000
        with self.assertRaises(ValueError):
            self.write()
        self.records[-1]["world_rows"][3]=0
        self.records[0]["simulation_tick"]="authoritative"
        with self.assertRaises(ValueError):
            self.write()

    def test_sequence_and_hook_mismatch(self):
        self.event("bind_skater",x=0)
        self.records[-1]["sequence"]=5
        self.assertFalse(self.write()["recording_complete"])
        self.records[-1]["hook"]=1
        with self.assertRaises(ValueError):
            self.write()


class StagingTests(unittest.TestCase):
    def runtime_fixture(self, folder):
        folder.mkdir()
        binary=folder/"gonkskate-thug-runtime.dll"
        binary.write_bytes(b"synthetic staging fixture, not executable")
        implib=folder/"gonkskate-thug-runtime.lib";implib.write_bytes(b"synthetic import fixture")
        def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
        headers={"native/thug_adapter/include/"+name:sha(ROOT/"native/thug_adapter/include"/name)
            for name in ("gonkskate_thug_runtime.h","gonkskate_thug.h")}
        manifest={"mode":"library","test_hooks":False,"target":"windows","tick_hz":60,
            "upstream_commit":THUG_PIN,"runtime_abi_version":1,"adapter_source_sha256":headers,
            "executable_sha256":sha(binary),"import_library_sha256":sha(implib),
            "abi_header_sha256":headers["native/thug_adapter/include/gonkskate_thug_runtime.h"]}
        (folder/"manifest.json").write_text(json.dumps(manifest))
        return manifest

    def test_runtime_stage_hashes_and_production_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder=Path(temporary)/"runtime";manifest=self.runtime_fixture(folder)
            _,files=runtime_files(folder)
            self.assertEqual(len(files),6)
            (folder/"gonkskate-thug-runtime.dll").write_bytes(b"changed")
            with self.assertRaises(ValueError):runtime_files(folder)
            manifest["test_hooks"]=True
            (folder/"manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):runtime_files(folder)

    def test_frontend_runtime_handshake_and_copy_whitelist(self):
        source=ROOT/"external/skate3"
        if not (source/"src/skate3_native_render.cpp").exists():self.skipTest("Pinned upstream required")
        with tempfile.TemporaryDirectory(dir=ROOT/"build") as temporary:
            folder=Path(temporary);runtime=folder/"runtime";self.runtime_fixture(runtime)
            (runtime/"private-owner-file.txt").write_text("do not copy")
            destination=stage(source,folder/"source",runtime)
            app=(destination/"src/skate3_app_common.cpp").read_text()
            self.assertEqual(app.count("gonk_thug_runtime_abi_version()"),1)
            self.assertNotIn("gonk_thug_runtime_step(",app)
            self.assertNotIn("private-owner-file.txt",str(list(destination.rglob("*"))))
            manifest=json.loads((destination/"gonkskate-probe-manifest.json").read_text())
            self.assertFalse(manifest["thug_runtime"]["gameplay_attached"])
            self.assertFalse(manifest["retail_code_executed"])

    def test_pinned_stage_preserves_checkout_and_existing_output(self):
        source=ROOT/"external/skate3"
        if not (source/"src/skate3_native_render.cpp").exists():
            self.skipTest("Run scripts/setup-skate3-source.py for source-stage integration")
        (ROOT/"build").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"build") as temporary:
            destination=Path(temporary)/"source"
            before=git(source,"status","--porcelain")
            original=git(source,"show","HEAD:src/skate3_app_common.cpp").decode()
            stage(source,destination)
            patched=(destination/"src/skate3_app_common.cpp").read_text()
            restored=patched.removeprefix('#include "gonkskate_probe/integration/skate3_probe.h"\n')
            restored=restored.replace("\n  gonkskate::guest_probe::Start();","").replace("\n  gonkskate::guest_probe::Stop();","")
            self.assertEqual(restored,original)
            self.assertEqual(before,git(source,"status","--porcelain"))
            self.assertFalse((destination/"game/default.xex").exists())
            self.assertFalse((destination/"generated/skate3_init.h").exists())
            manifest=json.loads((destination/"gonkskate-probe-manifest.json").read_text())
            self.assertFalse(manifest["retail_code_executed"])
            self.assertEqual(len(manifest["hooks"]),10)
            sentinel=destination/"owner-data.txt"
            sentinel.write_text("preserve")
            with self.assertRaises(ValueError):
                stage(source,destination)
            self.assertEqual(sentinel.read_text(),"preserve")


if __name__=="__main__":
    unittest.main()
