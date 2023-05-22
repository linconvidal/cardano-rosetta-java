//package org.cardanofoundation.rosetta.consumer.kafka;
//
//import java.util.concurrent.CountDownLatch;
//import lombok.Getter;
//import org.apache.kafka.clients.consumer.ConsumerRecord;
//
//import org.cardanofoundation.rosetta.common.ledgersync.kafka.CommonBlock;
//import org.springframework.context.annotation.Profile;
//import org.springframework.kafka.annotation.KafkaListener;
//import org.springframework.stereotype.Component;
//
//@Component
//@Getter
//@Profile("test-integration")
//public class KafkaConsumer {
//  private CountDownLatch latch = new CountDownLatch(1);
//  private CommonBlock payload;
//
//  @KafkaListener(topics = "${test.topic}")
//  public void receive(ConsumerRecord<String, CommonBlock> consumerRecord) {
//    payload = consumerRecord.value();
//    latch.countDown();
//  }
//
//  public void resetLatch() {
//    latch = new CountDownLatch(1);
//  }
//}