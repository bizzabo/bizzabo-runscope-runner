import http.client
import json
import logging
import os
import sys
import threading
import time

logging.basicConfig(
    level=os.environ.get('LOG_LEVEL', logging.DEBUG),
    format="%(asctime)s : [%(levelname)s] : %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    try:
        bucket_list_file = sys.argv[1]
        params_file = sys.argv[2]

        bucket_list = _read_json_file(bucket_list_file)
        params = _read_json_file(params_file)

        threads = []
        results = {}
        for bucket in bucket_list:
            thread = threading.Thread(target=_run_tests, args=(results, bucket, params))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        _parse_results(results)
    except Exception as e:
        pass
    finally:
        logging.shutdown()


def _read_json_file(file_path: str) -> dict:
    with open(file_path, 'r') as json_file:
        return json.load(json_file)


def _run_tests(results: dict, bucket: dict, params: dict):
    bucket_name = bucket.get('name')
    bucket_result = {}

    bucket_uri = bucket['trigger_url'].split('https://api.runscope.com')[-1]

    http_conn = http.client.HTTPSConnection('api.runscope.com')
    http_conn.request('GET', bucket_uri, body=json.dumps(params), headers={})
    res = http_conn.getresponse()

    if res.status == http.HTTPStatus.CREATED:
        data = res.read().decode('utf-8')
        json_data = json.loads(data)
        trigger_json = json_data.get('data', {})

        test_runs = trigger_json.get('runs', [])

        logger.info('Bucket: `{}` started: {} test runs.'.format(bucket_name, len(test_runs)))

        while len(bucket_result.keys()) < len(test_runs):
            time.sleep(1)

            for test_run in test_runs:
                test_run_id = test_run.get('test_run_id')
                if test_run_id not in bucket_result:
                    result = _get_result(http_conn, bucket_name, test_run)
                    if result.get('result', None) in ['pass', 'fail']:
                        logger.debug(
                            'Result for bucket: `{}`, test: `{}` is: {}'
                                .format(bucket_name, test_run.get('test_name'), json.dumps(result['result']))
                        )
                        bucket_result[test_run_id] = result

        logger.info('Bucket: `{}` finished: {} test runs.'.format(bucket_name, len(test_runs)))
        results[bucket_name] = bucket_result


def _get_result(http_conn: http.client.HTTPSConnection, bucket: str, test_run: dict) -> dict:
    opts = {
        'bucket_key': test_run.get('bucket_key'),
        'test_id': test_run.get('test_id'),
        'test_run_id': test_run.get('test_run_id')
    }

    http_conn.request(
        'GET',
        '/buckets/{bucket_key}/tests/{test_id}/results/{test_run_id}'.format(**opts),
        headers={'Authorization': 'Bearer {}'.format(os.environ['RUNSCOPE_ACCESS_TOKEN'])}
    )

    res = http_conn.getresponse()
    test_name = test_run.get('test_name')
    logger.debug('Polling result for bucket: `{}`, test: `{}`'.format(bucket, test_name))

    if res.status == http.HTTPStatus.OK:
        data = res.read().decode('utf-8')
        json_data = json.loads(data)
        result_data = json_data.get('data', {})
        result_data['test_name'] = test_name
        return result_data

    return {}


def _parse_results(results: dict):
    total_failed = 0

    logger.info('{pattern} Test Results {pattern}'.format(pattern=('=' * 30)))

    for bucket_name in results.keys():
        bucket_result = results[bucket_name]

        test_results = bucket_result.values()
        pass_count = sum([r.get('result') == 'pass' for r in test_results])
        fail_count = sum([r.get('result') == 'fail' for r in test_results])

        if fail_count > 0:
            total_failed += fail_count
            logger.info('Bucket: `{}` has {} test runs passed. {} test runs failed.'
                        .format(bucket_name, pass_count, fail_count)
                        )
            for test_result in test_results:
                logger.warning(
                    "\t[FAILED] `{}`, test url: {}".format(test_result['test_name'], test_result['trigger_url'])
                )
        else:
            logger.info('Bucket: `{}` has passed all {} tests.'.format(bucket_name, pass_count))

        if total_failed == 0:
            logger.info("Execution succeeded")
        else:
            logger.critical("Execution failed")
            sys.exit(1)


if __name__ == '__main__':
    main()
