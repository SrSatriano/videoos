from __future__ import annotations

from app.database import SessionLocal
from app.models import Batch, RenderJob
from app.services.queue import recover_interrupted_jobs
from app.services.llm import generate_viral_hooks, generate_script_to_video


def test_recover_interrupted_jobs_poison_pill_protection():
    with SessionLocal() as db:
        from app.models import Asset, Template
        tpl = db.query(Template).first()
        if not tpl:
            tpl = Template(name="Tpl Teste", recipe_json="{}")
            db.add(tpl)
            db.flush()
        asset = db.query(Asset).first()
        if not asset:
            asset = Asset(filename="teste.mp4", stored_path="teste.mp4", file_size_bytes=1024)
            db.add(asset)
            db.flush()

        batch = Batch(name='Batch Teste Crash', template_id=tpl.id, total_jobs=2)
        db.add(batch)
        db.flush()

        # Job normal interrompido (attempts = 1) -> deve ser requeued
        job1 = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=tpl.id, status='processing', attempts=1)
        # Job poison pill interrompido 3 vezes -> deve ser failed
        job2 = RenderJob(batch_id=batch.id, asset_id=asset.id, template_id=tpl.id, status='processing', attempts=3)
        db.add_all([job1, job2])
        db.commit()


        recovered_count = recover_interrupted_jobs(db)
        assert recovered_count == 2

        db.refresh(job1)
        db.refresh(job2)
        assert job1.status == 'queued'
        assert job2.status == 'failed'
        assert 'poison pill' in job2.error_message.lower()


def test_generate_viral_hooks_heuristics():
    result = generate_viral_hooks('como economizar dinheiro')
    assert result['topic'] == 'como economizar dinheiro'
    assert len(result['hooks']) == 4
    formulas = [h['formula'] for h in result['hooks']]
    assert 'curiosidade' in formulas
    assert 'choque' in formulas
    assert 'beneficio_imediato' in formulas
    assert 'quebra_crenca' in formulas
    assert all(h['retention_score'] >= 80 for h in result['hooks'])


def test_generate_script_to_video_blocks():
    script = generate_script_to_video('automacao de canais dark')
    assert 'automacao de canais dark' in script['title']
    assert len(script['blocks']) == 5
    block_names = [b['block_name'] for b in script['blocks']]
    assert block_names == ['hook', 'context', 'solution', 'practical', 'cta']
