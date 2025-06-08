from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
import os
from transformers import pipeline
from datasets import load_dataset
import torch

MODEL_PATH = "./models/comadvisor"  # 파인튜닝된 모델 디렉토리 경로
MODEL = "./models/advise" 
print("🔧 모델 불러오는 중...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
print("✅ 모델 로딩 완료")


# 2. 데이터셋 로드 (jsonl 형식: {"prompt": "...", "completion": "..."})
def preprocess(example):
    full_text = example["prompt"] + " " + example["completion"]
    return tokenizer(full_text, truncation=True, padding="max_length", max_length=256)

dataset = load_dataset("json", data_files={"train": "./train.jsonl"})
tokenized_dataset = dataset["train"].map(preprocess)

# 3. 파인튜닝 설정
training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=2,
    num_train_epochs=3,
    save_steps=500,
    logging_steps=100,
    save_total_limit=2,
    fp16=True,
    push_to_hub=False,
    report_to="none"
)

data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=data_collator,
)

# 4. 학습
trainer.train()

# 5. 모델 저장
model.save_pretrained(MODEL)
tokenizer.save_pretrained(MODEL)