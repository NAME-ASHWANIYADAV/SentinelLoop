"""CLI parsing: the common options (--out-dir, --data-dir, --config-dir) are accepted before or after the subcommand."""
from sentinelloop import cli


def test_common_options_accepted_after_the_subcommand():
    a = cli.build_parser().parse_args(["run", "--subset", "FD001", "--fast", "--out-dir", "artifacts_demo"])
    assert a.out_dir == "artifacts_demo" and a.subset == "FD001" and a.fast and a.data_dir == "data/raw"
    b = cli.build_parser().parse_args(["retrain", "--subset", "FD003", "--simulate-new-data", "--out-dir", "artifacts_demo"])
    assert b.out_dir == "artifacts_demo" and b.simulate_new_data


def test_common_options_still_accepted_before_the_subcommand():
    a = cli.build_parser().parse_args(["--out-dir", "elsewhere", "audit"])
    assert a.out_dir == "elsewhere" and a.command == "audit"
