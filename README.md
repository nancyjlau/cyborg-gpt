testing gpt / other llms on the cyborg environment

- results will probably be much better with rl agent guiding llm instead of only llm planning
- maybe try fine tuning on task specific stuff (on oss models for now, costly for openai models)
- file used was [gpt4.py](gpt4.py)
- ignore [securitybot.py](testing/securitybot.py), it was unfinished attempt at reimplementing the [depending on yourself when you should](https://arxiv.org/pdf/2403.17674.pdf) paper

## gpt-4-turbo-2024-04-09

$6.65 - observation 1 - 100 steps with only sleep action for blue agent cost  
$0.94 - observation 2 - 26 steps  
$1.87 - observation 5 - 48 steps   
$3.76 - observation 7 - 48 steps  
$0.83 - observation 11 - 100 steps  

[observations 1 - $6.65](observations/observations-1.txt)  
[observations 2 - $0.94](observations/observations-20240413175508.txt)  
[observation 5 - $1.87](observations/observations-20240413192821.txt)  
[observation 7 - $3.76](observations/observations-20240413221357.txt)  
[observation 10 - $0.31](observations/observations-20240413233916)  
[observation 11 - $0.83](observations/observations-20240413235343.txt)  

## claude 3 opus - $5 free credit 
results later