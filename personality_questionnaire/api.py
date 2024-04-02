import argparse
from pathlib import Path
import numpy as np
from personality_questionnaire import bfi2, vasf, io


def cmd_bfi2(args):
    print('Welcome to the BFI-2 questionnaire!')

    if bool(args.skip_questions):
        answers_path = Path(args.output_dir) / f'{args.participant_id}_bfi2_answers_int.csv'

        if not answers_path.exists():
            print('Answers not found. Please run this script without --skip_questions first.')
            exit(3)

        answers = io.load_csv_int(answers_path, 60)
        result = bfi2.bfi2(answers)
        io.save_csv(Path(args.output_dir) / f'{args.participant_id}_ocean.csv', result['OCEAN'])
        io.save_csv(Path(args.output_dir) / f'{args.participant_id}_facet.csv', result['FACET'])
        print(f'Result for participant {args.participant_id}:')
        print('OCEAN:', ', '.join(map(str, np.round(result['OCEAN'][0, :], decimals=2))))
        print('FACET:', ', '.join(map(str, np.round(result['FACET'][0, :], decimals=2))))
        print('You can find the results in the files *_bfi2_answers_int.csv, *_ocean.csv, *_facet.csv')
        exit(0)

    print('Please write a number to each statement to indicate the extent to which you agree or disagree with that statement.')
    print('Here you can see the scale:')
    for k, v in bfi2.ANSWER.items(): print(f'\t{k}: {v}')
    print('Now, let\'s start!')
    print('I am someone who...')
    answers = []
    for i in range(1, len(bfi2.BFI2_QUESTIONNAIRE) + 1):

        while True:
            question = f'Q{i}: {bfi2.BFI2_QUESTIONNAIRE[i]} \nA{i}: '
            answer = input(question)

            if answer.lower() == 'quit':
                print('Exiting questionnaire...')
                exit(0)

            if not answer.isdigit() or int(answer) < 1 or int(answer) > 5:
                print(f'[Invalid answer] Please enter a number between 1 (Disagree strongly) and 5 (Agree strongly) or "quit" to exit.')
            else:
                answers.append(answer)
                break

    result = bfi2.bfi2([answers])
    io.save_csv_int(Path(args.output_dir) / f'{args.participant_id}_bfi2_answers_int.csv', [answers])
    io.save_csv(Path(args.output_dir) / f'{args.participant_id}_ocean.csv', result['OCEAN'])
    io.save_csv(Path(args.output_dir) / f'{args.participant_id}_facet.csv', result['FACET'])

    print(f'Result for participant {args.participant_id}:')
    print('OCEAN:', ', '.join(map(str, np.round(result['OCEAN'][0, :], decimals=2))))
    print('FACET:', ', '.join(map(str, np.round(result['FACET'][0, :], decimals=2))))
    print('You can find the results in the files *_bfi2_answers_int.csv, *_ocean.csv, *_facet.csv')


def cmd_vasf(args):
    print(f'Welcome to the VAS-F ({args.vasf_tag}) questionnaire!')

    if bool(args.skip_questions):
        pre_answers_path = Path(args.output_dir) / f'{args.participant_id}_vasf-pre_answers_int.csv'
        if not pre_answers_path.exists():
            print('Pre-experiment answers not found. Please run this script with --vasf_tag pre first.')
            exit(3)
        post_answers_path = Path(args.output_dir) / f'{args.participant_id}_vasf-post_answers_int.csv'
        if not post_answers_path.exists():
            print('Post-experiment answers not found. Please run this script with --vasf_tag post first.')
            exit(3)
        pre_answers = io.load_csv_int(pre_answers_path, 18)
        post_answers = io.load_csv_int(post_answers_path, 18)
        result = vasf.vasf(pre_answers, post_answers)
        io.save_csv(Path(args.output_dir) / f'{args.participant_id}_vasf-relative.csv', result)
        print(f'Result for participant {args.participant_id}:')
        print('Pre-experiment VAS-F:', ', '.join(map(str, pre_answers[0, :])))
        print('Post-experiment VAS-F:', ', '.join(map(str, post_answers[0, :])))
        print('Relative VAS-F:', ', '.join(map(str, result[0, :])))
        exit(0)

    print('Please write a number between 0 and 10 to each statement to indicate how you are feeling right now.')
    print('The extreme values of the scale are mentioned within the questions.')
    print('Now, let\'s start!')
    answers = []
    for i in range(1, len(vasf.VASF_QUESTIONNAIRE) + 1):
        while True:
            if i in list(range(1, 13)) + [17, 18]:
                question = f'Q{i}: 0 means "{vasf.ANSWER_DIMS[i][0]} {vasf.VASF_QUESTIONNAIRE[i]}", while and 10 means "{vasf.ANSWER_DIMS[i][1]} {vasf.VASF_QUESTIONNAIRE[i]}" \nA{i}: '
            else: # i in range(13, 17):
                question = f'Q{i}: 0 means "{vasf.VASF_QUESTIONNAIRE[i]} {vasf.ANSWER_DIMS[i][0]}", while and 10 means "{vasf.VASF_QUESTIONNAIRE[i]} {vasf.ANSWER_DIMS[i][1]}" \nA{i}: '
            answer = input(question)

            if answer.lower() == 'quit':
                print('Exiting questionnaire...')
                exit(0)

            if not answer.isdigit() or int(answer) < 0 or int(answer) > 10:
                print(f'[Invalid answer] Please enter a number between 0 and 10 or "quit" to exit.')
            else:
                answers.append(int(answer))
                break

    if args.vasf_tag == 'pre':
        io.save_csv_int(Path(args.output_dir) / f'{args.participant_id}_vasf-{args.vasf_tag}_answers_int.csv', [answers])
        print('You can find the results in the file *_answers_int.csv')
        print('Please proceed with the experiment and run this script again after the experiment to get the post-experiment results.')
        exit(1)

    pre_answers_path = Path(args.output_dir) / f'{args.participant_id}_vasf-pre_answers_int.csv'
    if not pre_answers_path.exists():
        print('Pre-experiment answers not found. Please run this script with --vasf_tag pre first.')
        exit(2)

    pre_answers = io.load_csv_int(pre_answers_path, 18)
    result = vasf.vasf(pre_answers, answers)
    io.save_csv_int(Path(args.output_dir) / f'{args.participant_id}_vasf-{args.vasf_tag}_answers_int.csv', [answers])
    io.save_csv(Path(args.output_dir) / f'{args.participant_id}_vasf-relative.csv', result)
    print(f'Result for participant {args.participant_id}:')
    print('Pre-experiment VAS-F:', ', '.join(map(str, pre_answers[0, :])))
    print('Post-experiment VAS-F:', ', '.join(map(str, answers)))
    print('Relative VAS-F:', ', '.join(map(str, result[0, :])))


def main():
    parser = argparse.ArgumentParser(description='Experiment Questionnaire API')
    parser.add_argument('--participant_id', type=str, required=True, help='Participant ID')
    parser.add_argument('--questionnaire', type=str, required=True, help='Questionnaire to process (bfi2, vasf)')
    parser.add_argument('--vasf_tag', type=str, required=False, choices=['pre', 'post'], default='pre', help='pre or post VAS-F experiment')
    parser.add_argument('--skip_questions', action='store_true', help='Skip the questionnaire, calculate results from saved answers')
    parser.add_argument('--output_dir', type=str, required=False, help='Output directory', default='data')
    args = parser.parse_args()


    if args.questionnaire == 'vasf':
        cmd_vasf(args)
    elif args.questionnaire == 'bfi2':
        cmd_bfi2(args)

if __name__ == '__main__':
    main()