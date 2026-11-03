"""One bounded, fail-closed reproduction command for the four research tracks."""
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

from deviation.simulator.runner import implementation_sha256
from deviation.verification.benchmark import timing_summary
from .bridge import same_science, replay_pilot, replay_recorded, verify_source_episode, compare_attack_bundle
from .provenance import PINS, environment, preservation_audit, read, repository, sha, source, write


class Reproduction:
    def __init__(self, out, cache, *, download=False):
        self.root = repository(); self.out = Path(out).resolve(); self.cache = Path(cache).resolve()
        if self.out == self.root or self.root in self.out.parents and self.out.parts[len(self.root.parts)] in {'src','tests','docs','artifacts','experiments','data','.git'}:
            raise ValueError('OUTPUT_MUST_NOT_OVERWRITE_REPOSITORY_EVIDENCE')
        if self.out.exists() and any(self.out.iterdir()): raise ValueError('OUTPUT_MUST_BE_EMPTY')
        self.out.mkdir(parents=True, exist_ok=True)
        self.download = download; self.steps = []; self.rebindings = {}; self.files = {}
        self.integration_source={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}

    def call(self, name, args, *, pinned=None):
        command = [sys.executable] + ([] if pinned else ['-I']) + list(map(str,args))
        log = self.out/'logs'/(name+'.log'); log.parent.mkdir(exist_ok=True)
        print(name, flush=True); start = perf_counter()
        with log.open('w') as stream:
            result = subprocess.run(command, cwd=self.root, env=environment(pinned), stdout=stream, stderr=subprocess.STDOUT)
        self.steps.append({'step':name, 'source':PINS[pinned] if pinned else 'CURRENT_INSTALLED_PACKAGE',
            'exit_code':result.returncode, 'seconds':perf_counter()-start})
        write(self.out/'execution.json', {'version':'integration-execution-1','steps':self.steps,
            'new_inference_calls':0, 'final_holdout_accessed':False})
        if result.returncode:
            raise RuntimeError('REPRODUCTION_FAILED: '+name+'; see '+str(log))

    def retain(self, path):
        p = Path(path)
        self.files[str(p.relative_to(self.out))] = sha(p)

    def equal(self, expected, actual):
        if Path(expected).read_bytes() != Path(actual).read_bytes():
            raise ValueError('STRICT_ARTIFACT_MISMATCH: '+str(expected))
        self.retain(actual)

    def compatible(self, name, expected, actual):
        self.rebindings[name] = same_science(read(expected), read(actual))
        self.retain(actual)

    def bundle_files(self, expected, actual, *, exact):
        for path in sorted(Path(expected).rglob('*')):
            if not path.is_file() or path.suffix not in {'.json','.jsonl'}: continue
            relative = path.relative_to(expected); other = Path(actual)/relative
            if path.name in {'manifest.json','audit_manifest.json'}:
                if exact: self.equal(path, other)
            elif path.suffix == '.jsonl':
                if exact: self.equal(path, other)
                else:
                    old=[json.loads(x) for x in path.read_text().splitlines()]
                    new=[json.loads(x) for x in other.read_text().splitlines()]
                    self.rebindings[str(other.relative_to(self.out))]=same_science(old,new)
                    self.retain(other)
            elif exact: self.equal(path, other)
            else: self.compatible(str(other.relative_to(self.out)), path, other)

    def historical(self):
        fixture='tests/fixtures/simulator/two_task.json'; market='tests/fixtures/markets/two_task.json'
        for name, sf, mf in [('phase2','two_task',None), ('phase3','v0_3_source','two_task'),
                            ('phase4','phase4_source','phase4_source'), ('benchmark','phase5_source','phase5_source')]:
            for module, arg, folder in [('simulator',fixture,sf),('markets',market,mf)]:
                if folder is None: continue
                dest=self.out/'historical'/name/module
                expected=self.root/'artifacts'/module/folder
                self.call(name+'-'+module,['-m','deviation.'+module,arg,'--out',dest,'--verify',expected/'receipts.json'],pinned=name)
                self.bundle_files(expected,dest,exact=True)
        expected=self.root/'artifacts/attacks/phase4'; dest=self.out/'historical/phase4'
        self.call('phase4-attack',['-m','deviation.attacks','replay',expected/'selected','--out',dest/'selected'],pinned='phase4')
        self.bundle_files(expected/'selected',dest/'selected',exact=True)
        for command, filename in [('campaign','campaign.json'),('sensitivity','sensitivity.json')]:
            arg='experiments/adversarial_protocol.json' if command=='campaign' else expected/'selected'
            self.call('phase4-'+command,['-m','deviation.attacks',command,arg,'--out',dest/command],pinned='phase4')
            self.equal(expected/filename,dest/command/filename)
        dest=self.out/'historical/producer'; expected=self.root/'artifacts/attacks/certified'
        self.call('producer-examples',['-m','deviation.attacks.certified','examples','--out',dest,'--verify',expected],pinned='producer')
        self.bundle_files(expected,dest,exact=True)
        self.call('producer-standalone',['-m','deviation.attacks.certified','verify',expected/'scenario.json',expected/'small-lmsr.certificate.json'],pinned='producer')
        dest=self.out/'historical/verification'; expected=self.root/'artifacts/verification'
        self.call('verification-81',['-m','deviation.verification','--out',dest,'--no-timings','--verify',expected/'results.json'],pinned='verification')
        self.equal(expected/'results.json',dest/'results.json'); self.equal(expected/'results.csv',dest/'results.csv')
        self.call('verification-archive',[str(Path(source('verification').name)/'scripts/check_certificate_archive.py'),str(expected)],pinned='verification')
        self.call('verification-ordinary-exact',[str(Path(source('verification').name)/'scripts/certificate_ordinary_exact.py'),str(dest)],pinned='verification')
        self.equal(expected/'ordinary_exact.json',dest/'ordinary_exact.json')
        dest=self.out/'historical/benchmark'; expected=self.root/'artifacts/benchmark/phase5'
        args=['-m','deviation.evaluation','--cache',self.cache,'--out',dest,'--verify',expected/'results.json']
        if self.download: args.append('--download')
        self.call('benchmark-full',args,pinned='benchmark')
        for file in ['results.json','recorded_table.csv','synthetic_table.csv','plot_data.json','REPORT.md','manifest.json']:
            self.equal(expected/file,dest/file)
        dest=self.out/'historical/agents'; expected=self.root/'artifacts/llm_agents'
        self.call('agent-controls',['-m','deviation_llm_agents','controls','--out',dest/'controls.json'],pinned='agents')
        self.equal(expected/'controls.json',dest/'controls.json')
        self.call('agent-transport',['-m','deviation_llm_agents','replay',expected/'test_transport_episode.json','--out',dest/'test_transport_replay.json'],pinned='agents')
        self.equal(expected/'test_transport_replay.json',dest/'test_transport_replay.json')
        self.call('agent-real-pilot',['-m','deviation_llm_agents.pilot','--verify',expected/'real_pilot.json','--out',dest/'real_pilot_replay.json'],pinned='agents')
        self.equal(expected/'real_pilot_replay.json',dest/'real_pilot_replay.json')
        self.call('agent-summary',[str(Path(source('agents').name)/'scripts/summarize_llm_pilot.py'),expected/'real_pilot.json','--out',dest],pinned='agents')
        for file in ['real_pilot_summary.json','real_pilot_summary.csv']: self.equal(expected/file,dest/file)
        self.call('agent-publication-audit',[str(Path(source('agents').name)/'scripts/audit_llm_pilot_privacy.py'),expected/'real_pilot.json','--out',dest/'real_pilot_publication_audit.json'],pinned='agents')
        self.equal(expected/'real_pilot_publication_audit.json',dest/'real_pilot_publication_audit.json')

    def current(self):
        for module in ['simulator','markets']:
            dest=self.out/'current'/module
            self.call('current-'+module,['-m','deviation.'+module,'tests/fixtures/'+module+'/two_task.json','--out',dest])
            self.compatible(module,self.root/'artifacts'/module/'phase5_source/receipts.json',dest/'receipts.json')
        dest=self.out/'current/producer'; expected=self.root/'artifacts/attacks/certified'
        self.call('current-producer',['-m','deviation.attacks.certified','examples','--out',dest])
        self.bundle_files(expected,dest,exact=False)
        dest=self.out/'current/verification'; expected=self.root/'artifacts/verification'
        self.call('current-verification-81',['-m','deviation.verification','--out',dest,'--no-timings'])
        self.compatible('verification-results',expected/'results.json',dest/'results.json')
        self.equal(expected/'results.csv',dest/'results.csv')
        entries=read(expected/'proof_manifest.json')['proofs']
        for entry in entries:
            case=entry['case']; actual=dest/'proofs'/(case+'.json')
            old=json.loads(gzip.decompress((expected/'proofs'/(case+'.json.gz')).read_bytes()))
            self.rebindings['proofs/'+case]=same_science(old,read(actual)); self.retain(actual)
        self.call('current-ordinary-exact',['scripts/certificate_ordinary_exact.py',dest])
        self.compatible('ordinary-exact',expected/'ordinary_exact.json',dest/'ordinary_exact.json')
        dest=self.out/'current/benchmark'; expected=self.root/'artifacts/benchmark/phase5'
        args=['-m','deviation.evaluation','--cache',self.cache,'--out',dest]
        if self.download: args.append('--download')
        self.call('current-benchmark-full',args)
        self.compatible('benchmark-results',expected/'results.json',dest/'results.json')
        self.retain(dest/'REPORT.md')
        for file in ['recorded_table.csv','synthetic_table.csv','plot_data.json']:
            self.equal(expected/file,dest/file)
        expected=self.root/'artifacts/llm_agents'; dest=self.out/'current/agents'
        self.call('current-agent-controls',['-m','deviation_llm_agents','controls','--out',dest/'controls.json'])
        self.equal(expected/'controls.json',dest/'controls.json')
        transport=read(expected/'test_transport_episode.json')
        verify_source_episode(transport['scenario'],transport['sidecar'])
        write(dest/'transport.json',replay_recorded(transport['scenario'],transport['sidecar'])); self.retain(dest/'transport.json')
        write(dest/'pilot.json',replay_pilot(read(expected/'real_pilot.json'))); self.retain(dest/'pilot.json')
        from deviation.attacks.evidence import load_bundle, discover, write_bundle
        original=load_bundle(self.root/'artifacts/attacks/phase4/selected')
        bundle=discover(original['scenario'],original['controller'],original['mechanism'],**original['options'])
        self.rebindings['current-attack']=compare_attack_bundle(original,bundle)
        dest=self.out/'current/attack'; write_bundle(bundle,dest)
        self.retain(dest/'evidence.json')
        from deviation.attacks.sensitivity import sensitivity
        value=sensitivity(bundle); write(dest/'sensitivity.json',value)
        self.compatible('current-sensitivity',self.root/'artifacts/attacks/phase4/sensitivity.json',dest/'sensitivity.json')
        self.call('current-attack-campaign',['-m','deviation.attacks','campaign','experiments/adversarial_protocol.json','--out',self.out/'current/campaign'])
        self.compatible('current-campaign',self.root/'artifacts/attacks/phase4/campaign.json',self.out/'current/campaign/campaign.json')

    def statistics(self):
        base=self.root/'artifacts/verification'; result=read(base/'results.json'); timing=read(base/'timings.json')
        if timing['results_sha256'] != result['sha256']: raise ValueError('TIMING_RESULTS_BINDING')
        summary=timing_summary(result['rows'],timing['samples'],read(self.root/'experiments/certificate_benchmark.json'))
        if summary != timing['summary']: raise ValueError('PUBLISHED_TIMING_STATISTIC_CHANGED')
        write(self.out/'statistics.json',{'recorded_timing_summary_recomputed':summary,
            'interpretation':'Original measured samples; no claim to reproduce identical wall times.'})
        self.retain(self.out/'statistics.json')

    def plots(self):
        b=self.out/'historical/benchmark'
        self.call('benchmark-plots',['scripts/plot_benchmark.py',b],pinned='benchmark')
        v=self.out/'historical/verification'
        shutil.copyfile(self.root/'artifacts/verification/timings.json',v/'timings.json')
        self.call('certificate-plots',['scripts/report_certificate_benchmark.py',v],pinned='verification')
        if (self.root/'artifacts/verification/plot_data.json').read_bytes() != (v/'plot_data.json').read_bytes():
            raise ValueError('CERTIFICATE_PLOT_DATA_CHANGED')
        for folder, manifest in [(b,'plot_manifest.json'),(v,'figure_manifest.json')]:
            m=read(folder/manifest)
            if manifest=='plot_manifest.json':
                if m['matplotlib']!='3.10.7' or m['input_plot_data_sha256']!=sha(folder/'plot_data.json') or m['plot_script_sha256']!=sha(self.root/'scripts/plot_benchmark.py'):
                    raise ValueError('PLOT_INPUT_BINDING')
                images={folder/name:value for name,value in m['figures'].items()}
            else:
                images={folder/'figures'/name:value for name,value in m['figures'].items()}
                for name,value in m.items():
                    if name=='figures': continue
                    p=self.root/'scripts'/name if name.endswith('.py') else folder/name
                    if sha(p)!=value: raise ValueError('FIGURE_INPUT_BINDING')
            for p,value in images.items():
                if sha(p)!=value: raise ValueError('FIGURE_OUTPUT_BINDING')

    def run(self, *, plots=False, verify=None):
        try:
            preserved=preservation_audit()
            write(self.out/'preservation.json',preserved); self.retain(self.out/'preservation.json')
            self.historical(); self.current(); self.statistics()
            if plots: self.plots()
            write(self.out/'rebindings.json',self.rebindings); self.retain(self.out/'rebindings.json')
            adapter=Path(__file__).parent
            manifest={'version':'backend-integration-reproduction-1','source_pins':PINS,
                'engine_package_sha256':implementation_sha256(),
                'integration_source':self.integration_source,
                'files':dict(sorted(self.files.items())), 'new_inference_calls':0,
                'final_holdout_accessed':False, 'scientific_success_criteria_changed':False}
            if self.integration_source != {p.name:sha(p) for p in sorted(adapter.glob('*.py'))}:
                raise ValueError('INTEGRATION_SOURCE_CHANGED_DURING_RUN')
            write(self.out/'manifest.json',manifest)
            if verify and manifest != read(verify): raise ValueError('INTEGRATED_STRICT_MANIFEST_MISMATCH')
            write(self.out/'SUCCESS.json',{'status':'REPRODUCED_NOT_RELEASED','manifest_sha256':sha(self.out/'manifest.json')})
            print('All historical and current numerical evidence reproduced; no release or breakthrough claim.',flush=True)
            return manifest
        except BaseException as error:
            write(self.out/'FAILURE.json',{'exception':type(error).__name__,'message':str(error)})
            raise
