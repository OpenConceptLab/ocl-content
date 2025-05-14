import json
import ndjson
import logging
import urllib.parse
LOCAL_FILE = 'C:/Users/jamlung/Documents/SNOMED-GPS/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/OCL Processing - SNOMED-GPS 2023/SNOMED-GPS-2023-bulk-import.json'
OCL_FILE = 'C:/Users/jamlung/Documents/SNOMED-GPS/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/OCL Processing - SNOMED-GPS 2023/Prod Load/SNOMED~1/export.json'
DIFF_FILE = 'C:/Users/jamlung/Documents/SNOMED-GPS/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/SnomedINTL_GPSRelease_PRODUCTION_20230731T120000Z/OCL Processing - SNOMED-GPS 2023/Prod Load/diff.json'
logger = logging.getLogger('diff')
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
with open(LOCAL_FILE, 'r', encoding="utf-8-sig") as f:
    local_data = ndjson.load(f)
with open(OCL_FILE, 'r', encoding="utf-8-sig") as f:
    ocl_data = json.load(f)
def type_equals(t): return lambda x: x['type'] == t
def q(s): return urllib.parse.quote_plus(str(s))
def get_mapping_key(mapping):
    if 'to_concept_url' in mapping and mapping['to_concept_url']:
        return '%s--%s--%s' % (mapping['from_concept_url'], mapping['map_type'], mapping['to_concept_url'])
    return '%s--%s--%sconcepts/%s/' % (mapping['from_concept_url'], mapping['map_type'], mapping['to_source_url'], q(mapping['to_concept_code']))
def compare_concepts(a, b):
    properties_to_compare = ['concept_class', 'datatype', 'retired']
    #properties_to_compare = ['concept_class', 'datatype']
    for p in properties_to_compare:
        if not a[p] == b[p]:
            logger.warning('Concept "%s" mismatch on %s: "%s" <> "%s"' % (
                a['id'], p, a[p], b[p]))
def compare_mappings(a, b):
    pass
out = open(DIFF_FILE, 'w')
out.write('{\n')
ocl_concepts_cache = {}
ocl_concepts = ocl_data['concepts']
for c in ocl_concepts:
    if c['id'] in ocl_concepts_cache:
        # This shouldn't happen
        logger.error('OCL has more than one concept with id "%s"' % c['id'])
    else:
        ocl_concepts_cache[c['id']] = c
out.write('  "missing_concepts":[')
removed_concepts = {}
first = True
c_count = 0
for c in filter(type_equals('Concept'), local_data):
    if not c['id'] in ocl_concepts_cache:
        if c['id'] in removed_concepts:
            removed_concepts[c['id']] += 1
            logger.error('Multiple copies of local concept "%s" (n=%i)\n%s' %
                         (c['id'], removed_concepts[c['id']], json.dumps(c)))
        else:
            logger.warning('OCL does not have concept with id "%s"' % c['id'])
            if not first:
                out.write(',')
            out.write('\n    %s' % json.dumps(c))
            first = False
    else:
        compare_concepts(c, ocl_concepts_cache[c['id']])
        # Remove concept from cache (if 1:1 match, cache should end up empty when loop ends)
        del ocl_concepts_cache[c['id']]
        removed_concepts[c['id']] = 1

    c_count += 1
if not first:
    out.write('\n  ')
out.write('],\n')
# Any concepts remaining in cache represent extra OCL entries
out.write('  "extra_concepts": [')
first = True
for c in ocl_concepts_cache:
    ###logger.warning('OCL has extra concept with id "%s"' % c['id'])
    if not first:
        out.write(',')
    out.write('\n    %s' % json.dumps(c))
    first = False
    # logger.debug('DELETE %s/orgs/%s/concepts/%s/' % ('', c['owner'], c['id']))
if not first:
    out.write('\n  ')
out.write('],\n')
out.write('  "Concepts compared": ' + str(c_count) + ',\n')
ocl_mappings_cache = {}
ocl_mappings = ocl_data['mappings']
for m in ocl_mappings:
    key = get_mapping_key(m)
    if m['retired'] == True:
        continue  # skip retired mappings
    if key in ocl_mappings_cache:
        logger.error('OCL has more than one mapping for "%s"' % key)
    else:
        ocl_mappings_cache[key] = m
out.write('  "missing_mappings": [')
removed_mappings = {}
first = True
m_count = 0
for m in filter(type_equals('Mapping'), local_data):
    key = get_mapping_key(m)
    if not key in ocl_mappings_cache:
        if key in removed_mappings:
            removed_mappings[key] += 1
            logger.error('Multiple copies of local mapping "%s" (n=%i)\n%s' %
                         (key, removed_mappings[key], json.dumps(m)))
        else:
            logger.warning('OCL does not have mapping "%s"' % key)
            if not first:
                out.write(',')
            out.write('\n    %s' % json.dumps(m))
            first = False
    else:
        compare_mappings(m, ocl_mappings_cache[key])
        # Remove mapping from cache (if 1:1 match, cache should end up empty)
        del ocl_mappings_cache[key]
        removed_mappings[key] = 1
    m_count += 1
if not first:
    out.write('\n  ')
out.write('],\n')
out.write('  "Mappings compared": ' + str(m_count) + ',\n')
# Any mappings remaining in cache represent extra OCL entries
out.write('  "extra_mappings": [')
first = True
for m in ocl_mappings_cache:
    # logger.warning('OCL has extra mapping "%s"' % m)
    if ocl_mappings_cache[m]['retired'] != True:
        if not first:
            out.write(',')
        out.write('\n    %s' % json.dumps(ocl_mappings_cache[m]))
        first = False
if not first:
    out.write('\n  ')
out.write(']\n')
out.write('}')
out.close()
print('done')
