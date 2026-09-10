from ml.data.loader import load_delay_data
from ml.data.splitting import temporal_split


def test_temporal_split_is_chronological():
    train,valid,test=temporal_split(load_delay_data())
    assert train.snapshot_month.max()<valid.snapshot_month.min()
    assert valid.snapshot_month.max()<test.snapshot_month.min()
    assert (len(train),len(valid),len(test))==(6065,2148,2155)
