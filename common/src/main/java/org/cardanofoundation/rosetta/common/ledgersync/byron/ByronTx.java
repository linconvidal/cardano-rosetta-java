package org.cardanofoundation.rosetta.common.ledgersync.byron;

import lombok.*;

import java.util.List;

@Getter
@AllArgsConstructor
@NoArgsConstructor
@ToString
@EqualsAndHashCode
@Builder
public class ByronTx {

  private List<ByronTxIn> inputs;
  private List<ByronTxOut> outputs;
  private String txHash;

  //TODO -- Attributes
}
