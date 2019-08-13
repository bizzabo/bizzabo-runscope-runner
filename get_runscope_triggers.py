
import json
import requests
import sys

BRANCH_INFIX = "BRANCH"

def extract_relevant_tests_from_bucket(bucketInfo, brunchName, authorization):
	url = bucketInfo["tests_url"]
	headers  = {"Content-Type": "application/json", "Authorization": "Bearer " + authorization}
	response =  requests.get(url = url, headers = headers)

	accumulate = []

	for testInfo in response.json()['data']:
		branchInfixAndName = BRANCH_INFIX + " " + brunchName
		descriptionContainsBranchName = (testInfo['description'] is not None) and (branchInfixAndName in testInfo['description'])
		descriptionNotContainsAnyBranch = (testInfo['description'] is None) or ((testInfo['description'] is not None) and (BRANCH_INFIX not in testInfo['description']))
		if descriptionContainsBranchName or descriptionNotContainsAnyBranch:
			accumulate.append(testInfo['trigger_url'])
	return accumulate




def get_relevant_tests_triggers(readFile, branchName, authorization):

	testTriggers = []

	with open(readFile, 'r') as file:
		bucketsInfo = json.load(file)
		for bucketInfo in bucketsInfo:
			bucketTestTriggers = extract_relevant_tests_from_bucket(bucketInfo, branchName, authorization)
			testTriggers.extend(bucketTestTriggers)

	return testTriggers

def write_to_file(input, outputeFile):
	outFile = open(outputeFile, "w")
	outFile.write(str(input))
	outFile.close()


if __name__ == '__main__':
	readFile = sys.argv[1]
	writeFile = sys.argv[2]
	branchName = sys.argv[3]
	authorization = sys.argv[4]
	relevantTestsTriggers = get_relevant_tests_triggers(readFile, branchName, authorization)
	write_to_file(relevantTestsTriggers, writeFile)