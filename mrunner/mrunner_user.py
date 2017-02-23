def job_main_(neptune_ctx, args, exp_dir_path):
    raise NotImplementedError

def mrunner_main(job_main, create_parser_fun):
    import os
    if os.environ.get('MRUNNER_UNDER_NEPTUNE', '0') == '1':
        # running under neptune
        from deepsense import neptune
        ctx = neptune.Context()
        args = ctx.params
        exp_dir_path = ctx.dump_dir_url
    else:
        parser = create_parser_fun()
        args = parser.parse_args()
        ctx = None
        exp_dir_path = os.environ.get('MRUNNER_EXP_DIR_PATH', '.')

    job_main(ctx, args, exp_dir_path)
